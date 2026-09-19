import asyncio
import json
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.simulator.home_simulator import simulator_instance

ws_router = APIRouter(tags=["WebSocket Streaming"])


class ConnectionManager:
    """Manages active WebSocket connections from frontend clients."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)


def _state_payload() -> dict:
    return simulator_instance.get_current_home_state().model_dump(mode="json")


@ws_router.websocket("/ws/home")
async def websocket_home_stream(websocket: WebSocket):
    """Stream simulator state without starting or invoking the future agent."""
    await websocket.accept()
    try:
        await websocket.send_json({"event": "connected", "state": _state_payload()})
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                action = message.get("action")
                if action == "step":
                    simulator_instance.engine.step(float(message.get("dt_minutes", 1.0)))
                elif action == "pause":
                    simulator_instance.engine.pause()
                elif action == "start":
                    simulator_instance.engine.start()
                elif action == "reset":
                    simulator_instance.engine.reset()
                elif action not in (None, "state"):
                    await websocket.send_json({"event": "error", "detail": "Unsupported WebSocket action"})
                    continue
                await websocket.send_json({"event": "state_update", "state": _state_payload()})
            except asyncio.TimeoutError:
                if simulator_instance.engine.is_running:
                    simulator_instance.engine.step(1.0)
                await websocket.send_json({"event": "state_update", "state": _state_payload()})
    except (WebSocketDisconnect, ValueError, TypeError):
        manager.disconnect(websocket)


manager = ConnectionManager()


@ws_router.websocket("/ws/simulation")
async def websocket_simulation_stream(websocket: WebSocket):
    """
    Continuous real-time streaming endpoint for telemetry and agent decisions.
    Clients receive telemetry on each tick, and can send commands ('step', 'pause', etc.).
    """
    await manager.connect(websocket)
    try:
        # Initial greeting with current state
        initial_state = simulator_instance.get_current_home_state().model_dump(mode="json")
        await websocket.send_json({
            "event": "connected",
            "state": initial_state
        })

        while True:
            # Legacy stream retained for compatibility; it never invokes the
            # autonomous agent during Prompt 3.
            try:
                data_str = await asyncio.wait_for(websocket.receive_text(), timeout=2.5)
                data = json.loads(data_str)
                action = data.get("action")
                if action == "step":
                    state = simulator_instance.engine.step(1.0).model_dump(mode="json")
                    await websocket.send_json({"event": "telemetry_update", "state": state})
            except asyncio.TimeoutError:
                # Regular background tick
                state = simulator_instance.engine.step(dt_minutes=1.0).model_dump(mode="json")
                await websocket.send_json({
                    "event": "telemetry_update",
                    "state": state
                })
    except (WebSocketDisconnect, ValueError, TypeError):
        manager.disconnect(websocket)
