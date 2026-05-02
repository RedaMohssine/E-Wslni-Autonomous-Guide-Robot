"""
robot-hub — small WebSocket relay deployed as its own Railway service.

Architecture
------------
  Robot (cloud_bridge.py) ──persistent WSS────► /ws/robot   (this hub)
                                                      ▲
  Chatbot (navigation.py) ────HTTPS POST───────► /dispatch/* (this hub)

Auth
----
Single shared bearer token from HUB_TOKEN env var. Both the robot and the
chatbot must present it. The hub refuses everything otherwise.

Concurrency
-----------
At most one robot WS connection is active. A new connection replaces the
previous one (the old socket is closed cleanly).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Optional

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hub")

HUB_TOKEN = os.getenv("HUB_TOKEN", "").strip()
if not HUB_TOKEN:
    logger.warning("HUB_TOKEN is not set — every request will be rejected (401/403).")


app = FastAPI(title="robot-hub", version="1.0")


# ───────────────────────── connection state ─────────────────────────────────


class RobotConnection:
    """Holds the single active robot WS + the latest /robot_status payload."""

    def __init__(self) -> None:
        self.ws: Optional[WebSocket] = None
        self.last_status: Optional[dict[str, Any]] = None
        self._lock = asyncio.Lock()

    async def attach(self, ws: WebSocket) -> None:
        async with self._lock:
            old = self.ws
            self.ws = ws
        if old is not None:
            try:
                await old.close(code=1000, reason="replaced by newer connection")
            except Exception:
                pass

    async def detach(self, ws: WebSocket) -> None:
        async with self._lock:
            if self.ws is ws:
                self.ws = None

    async def send(self, message: dict[str, Any]) -> bool:
        ws = self.ws
        if ws is None:
            return False
        try:
            await ws.send_text(json.dumps(message, ensure_ascii=False))
            return True
        except Exception as exc:
            logger.warning("send to robot failed: %s", exc)
            return False


robot = RobotConnection()


# ───────────────────────── auth helpers ─────────────────────────────────────


def _check_bearer(authorization: Optional[str]) -> None:
    if not HUB_TOKEN:
        raise HTTPException(status_code=503, detail="hub not configured (HUB_TOKEN missing)")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    if authorization[7:].strip() != HUB_TOKEN:
        raise HTTPException(status_code=403, detail="invalid token")


# ───────────────────────── HTTP endpoints ───────────────────────────────────


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "robot_connected": robot.ws is not None}


@app.get("/status")
async def get_status(authorization: Optional[str] = Header(default=None)) -> dict[str, Any]:
    _check_bearer(authorization)
    return {
        "connected": robot.ws is not None,
        "last_status": robot.last_status,
    }


@app.post("/dispatch/navigation")
async def dispatch_navigation(
    payload: dict[str, Any],
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """Forward a navigation goal to the robot.

    The payload is the same JSON the chatbot used to publish to /navigation_goal
    via rosbridge:
      {
        "destination":  "Cafétéria",
        "matched_name": "Cafeteria",
        "coordinates":  {"latitude": <map_x>, "longitude": <map_y>},
        "building":     "Bâtiment Emines",
        "floor":        "RDC"
      }
    """
    _check_bearer(authorization)
    if robot.ws is None:
        raise HTTPException(status_code=503, detail="robot not connected")
    ok = await robot.send({"type": "navigation", "data": payload})
    if not ok:
        raise HTTPException(status_code=502, detail="failed to forward to robot")
    return {"status": "sent", "destination": payload.get("destination")}


@app.post("/dispatch/say")
async def dispatch_say(
    payload: dict[str, Any],
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """Forward a TTS request to the robot.

    Payload:
      {
        "text": "Bonjour, je vous emmène à la Cafétéria.",
        "lang": "fr"     // optional hint; the robot detects the language
                         // automatically if absent.
      }

    The robot synthesises locally with Cartesia and streams audio to its
    speaker — no audio bytes transit through this hub, only the text.
    """
    _check_bearer(authorization)
    if robot.ws is None:
        raise HTTPException(status_code=503, detail="robot not connected")
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="empty text")
    ok = await robot.send({
        "type": "say",
        "data": {"text": text, "lang": payload.get("lang")},
    })
    if not ok:
        raise HTTPException(status_code=502, detail="failed to forward to robot")
    return {"status": "sent", "chars": len(text)}


# ───────────────────────── robot WebSocket ──────────────────────────────────


@app.websocket("/ws/robot")
async def robot_ws(ws: WebSocket) -> None:
    # Robot side authenticates via the Authorization header on the WS handshake.
    authorization = ws.headers.get("authorization", "")
    if not HUB_TOKEN or not authorization.lower().startswith("bearer "):
        await ws.close(code=4401, reason="unauthorized")
        return
    if authorization[7:].strip() != HUB_TOKEN:
        await ws.close(code=4403, reason="invalid token")
        return

    await ws.accept()
    await robot.attach(ws)
    logger.info("robot connected")

    try:
        while True:
            text = await ws.receive_text()
            try:
                msg = json.loads(text)
            except json.JSONDecodeError:
                logger.debug("ignored non-JSON from robot: %r", text[:200])
                continue
            mtype = msg.get("type")
            if mtype == "status":
                robot.last_status = msg.get("data")
            elif mtype == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
            else:
                logger.debug("unhandled type from robot: %s", mtype)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("robot ws error: %s", exc)
    finally:
        await robot.detach(ws)
        logger.info("robot disconnected")
