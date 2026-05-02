"""
RobotVoiceService — sends text to the Railway hub, which forwards it to the
robot for local Cartesia synthesis. The browser does not play any audio in this
flow; the response speaks out of the robot's speaker.

Activation: both HUB_URL and HUB_TOKEN env vars must be set. Otherwise the
service no-ops cleanly so the chatbot keeps running for local development.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class RobotVoiceService:
    def __init__(self) -> None:
        self.hub_url = os.getenv("HUB_URL", "").strip().rstrip("/")
        self.hub_token = os.getenv("HUB_TOKEN", "").strip()

    @property
    def enabled(self) -> bool:
        return bool(self.hub_url and self.hub_token)

    def speak(self, text: str, lang: Optional[str] = None) -> dict:
        if not self.enabled:
            return {"status": "skipped", "reason": "HUB_URL/HUB_TOKEN not set"}

        text = (text or "").strip()
        if not text:
            return {"status": "skipped", "reason": "empty text"}

        body = {"text": text}
        if lang:
            body["lang"] = lang

        try:
            response = httpx.post(
                f"{self.hub_url}/dispatch/say",
                json=body,
                headers={"Authorization": f"Bearer {self.hub_token}"},
                timeout=5.0,
            )
            response.raise_for_status()
            return {"status": "sent", "via": "hub", "response": response.json()}
        except httpx.HTTPStatusError as exc:
            return {
                "status": "error",
                "via": "hub",
                "message": f"HTTP {exc.response.status_code}: {exc.response.text}",
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("speak via hub failed: %s", exc)
            return {"status": "error", "via": "hub", "message": str(exc)}
