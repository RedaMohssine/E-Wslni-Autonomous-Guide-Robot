import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
import websocket

from src.models import Destination
from src.services.location_catalog import LocationCatalogService


class NavigationService:
    """Service to handle destination lookup and navigation start requests.

    Two dispatch backends are supported:

    1. **hub** (preferred) — POSTs the navigation payload to the Railway-hosted
       robot-hub at ``HUB_URL/dispatch/navigation``, authenticated by
       ``HUB_TOKEN``. The hub forwards it to the robot via its persistent
       outbound WebSocket connection. No inbound port has to be exposed on
       the robot side.

    2. **rosbridge** (fallback / local dev) — opens a one-shot WebSocket to
       ``ROSBRIDGE_URL`` and publishes the JSON on ``ROS_NAVIGATION_TOPIC``.

    The hub backend is used whenever both ``HUB_URL`` and ``HUB_TOKEN`` are
    set; otherwise the service falls back to rosbridge if ``ROSBRIDGE_URL`` is
    set; otherwise the dispatch is skipped (useful for tests).
    """

    def __init__(
        self,
        locations_file: str = "data/locations.json",
        history_file: str = "data/Navigation history/history.json",
    ):
        self.catalog = LocationCatalogService(locations_file=locations_file)
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        self.hub_url = os.getenv("HUB_URL", "").strip().rstrip("/")
        self.hub_token = os.getenv("HUB_TOKEN", "").strip()

        self.rosbridge_url = os.getenv("ROSBRIDGE_URL", "").strip()
        self.navigation_topic = os.getenv("ROS_NAVIGATION_TOPIC", "/navigation_goal").strip()

    def list_locations(self):
        return self.catalog.list_locations()

    def get_categories(self):
        return ["All", *self.catalog.get_categories()]

    def search_locations(self, query: str = "", category: str = "All", limit: Optional[int] = None):
        return self.catalog.search_locations(query=query, category=category, limit=limit)

    def resolve_location(self, user_input: str) -> Optional[Destination]:
        return self.catalog.resolve_location(user_input)

    def prepare_navigation(self, user_input: str) -> Optional[dict]:
        location = self.resolve_location(user_input)
        if not location:
            return None

        # Use getattr so it doesn't crash if the attribute is missing
        matched = getattr(location, 'matched_name', None) or location.location_name

        return {
            "location_name": location.location_name,
            "category": location.category,
            "description": location.description,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "building": location.building,
            "floor": location.floor,
            "accessible": location.accessible,
            "matched_name": matched,
        }

    def get_coordinates(self, user_input: str):
        location = self.prepare_navigation(user_input)
        if not location:
            return None, None
        return location["latitude"], location["longitude"]

    def start_navigation(self, user_input: str, requested_by: str = "ui") -> Optional[dict]:
        navigation_payload = self.prepare_navigation(user_input)
        if not navigation_payload:
            return None

        dispatch_result = self._dispatch_navigation_command(navigation_payload)
        navigation_payload["dispatch"] = dispatch_result

        history = self._read_history()
        history.append(
            {
                "location": navigation_payload["location_name"],
                "matched_name": navigation_payload["matched_name"],
                "category": navigation_payload["category"],
                "date": datetime.now(timezone.utc).isoformat(),
                "requested_by": requested_by,
                "coordinates": {
                    "latitude": navigation_payload["latitude"],
                    "longitude": navigation_payload["longitude"],
                },
                "dispatch": dispatch_result,
            }
        )
        self._write_history(history)

        return navigation_payload

    def get_history(self, limit: Optional[int] = None) -> list[dict]:
        history = list(reversed(self._read_history()))
        return history[:limit] if limit else history

    def _read_history(self) -> list[dict]:
        try:
            with self.history_file.open("r", encoding="utf-8") as handle:
                try:
                    return json.load(handle)
                except json.JSONDecodeError:
                    return []
        except FileNotFoundError:
            return []

    def _write_history(self, history: list[dict]) -> None:
        with self.history_file.open("w", encoding="utf-8") as handle:
            json.dump(history, handle, indent=4, ensure_ascii=False)

    def _dispatch_navigation_command(self, navigation_payload: dict) -> dict:
        command_payload = {
            "destination": navigation_payload["location_name"],
            "matched_name": navigation_payload["matched_name"],
            "coordinates": {
                "latitude": navigation_payload["latitude"],
                "longitude": navigation_payload["longitude"],
            },
            "building": navigation_payload["building"],
            "floor": navigation_payload["floor"],
        }

        if self.hub_url and self.hub_token:
            return self._dispatch_via_hub(command_payload)
        if self.rosbridge_url:
            return self._dispatch_via_rosbridge(command_payload)
        return {
            "status": "skipped",
            "message": "No dispatch backend configured (set HUB_URL+HUB_TOKEN or ROSBRIDGE_URL).",
            "payload": command_payload,
        }

    def _dispatch_via_hub(self, command_payload: dict) -> dict:
        try:
            response = httpx.post(
                f"{self.hub_url}/dispatch/navigation",
                json=command_payload,
                headers={"Authorization": f"Bearer {self.hub_token}"},
                timeout=5.0,
            )
            response.raise_for_status()
            return {
                "status": "sent",
                "via": "hub",
                "url": self.hub_url,
                "response": response.json(),
                "payload": command_payload,
            }
        except httpx.HTTPStatusError as exc:
            return {
                "status": "error",
                "via": "hub",
                "message": f"HTTP {exc.response.status_code}: {exc.response.text}",
                "url": self.hub_url,
            }
        except Exception as exc:
            return {
                "status": "error",
                "via": "hub",
                "message": f"Failed to reach hub: {exc}",
                "url": self.hub_url,
            }

    def _dispatch_via_rosbridge(self, command_payload: dict) -> dict:
        try:
            ws = websocket.create_connection(self.rosbridge_url)
            msg = {
                "op": "publish",
                "topic": self.navigation_topic,
                "type": "std_msgs/String",
                "msg": {"data": json.dumps(command_payload)},
            }
            ws.send(json.dumps(msg))
            ws.close()
            return {
                "status": "sent",
                "via": "rosbridge",
                "topic": self.navigation_topic,
                "payload": command_payload,
            }
        except Exception as exc:
            return {
                "status": "error",
                "via": "rosbridge",
                "message": f"Failed to send navigation command: {exc}",
                "rosbridge_url": self.rosbridge_url,
                "topic": self.navigation_topic,
            }
