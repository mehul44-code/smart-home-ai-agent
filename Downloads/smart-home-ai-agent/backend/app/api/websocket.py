import asyncio
import json
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.simulator.home_simulator import simulator_instance
from backend.app.agent.core import agent_instance

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
        initial_state = simulator_instance.step(dt_minutes=0.0)
        await websocket.send_json({
            "event": "connected",
            "state": initial_state
        })

        while True:
            # Check for client messages with timeout
            try:
                data_str = await asyncio.wait_for(websocket.receive_text(), timeout=2.5)
                data = json.loads(data_str)
                action = data.get("action")
                
                if action == "step":
                    step_result = agent_instance.step()
                    await manager.broadcast({
                        "event": "agent_step",
                        "data": step_result
                    })
            except asyncio.TimeoutError:
                # Regular background tick
                state = simulator_instance.step(dt_minutes=1.0)
                await websocket.send_json({
                    "event": "telemetry_update",
                    "state": state
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
