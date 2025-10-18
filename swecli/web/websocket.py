"""WebSocket handler for real-time communication."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

from fastapi import WebSocket, WebSocketDisconnect

from swecli.web.state import get_state
from swecli.models.message import ChatMessage, Role


class WebSocketManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        state = get_state()
        state.add_ws_client(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        state = get_state()
        state.remove_ws_client(websocket)

    async def send_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a message to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def handle_message(self, websocket: WebSocket, data: Dict[str, Any]):
        """Handle incoming WebSocket message."""
        msg_type = data.get("type")

        if msg_type == "query":
            await self._handle_query(websocket, data)
        elif msg_type == "approve":
            await self._handle_approval(websocket, data)
        elif msg_type == "ping":
            await self.send_message(websocket, {"type": "pong"})
        else:
            await self.send_message(
                websocket,
                {"type": "error", "data": {"message": f"Unknown message type: {msg_type}"}}
            )

    async def _handle_query(self, websocket: WebSocket, data: Dict[str, Any]):
        """Handle a query message."""
        message = data.get("data", {}).get("message")
        if not message:
            await self.send_message(
                websocket,
                {"type": "error", "data": {"message": "Missing message field"}}
            )
            return

        # Add user message to state
        state = get_state()
        user_msg = ChatMessage(role=Role.USER, content=message)
        state.add_message(user_msg)

        # Broadcast user message to all clients
        await self.broadcast({
            "type": "user_message",
            "data": {
                "role": "user",
                "content": message,
            }
        })

        # Execute query with agent
        from swecli.web.agent_executor import AgentExecutor

        executor = AgentExecutor(state)
        await executor.execute_query(message, self)

    async def _handle_approval(self, websocket: WebSocket, data: Dict[str, Any]):
        """Handle an approval response from the web UI."""
        approval_data = data.get("data", {})
        approval_id = approval_data.get("approvalId")
        approved = approval_data.get("approved")

        if approval_id is None or approved is None:
            await self.send_message(
                websocket,
                {"type": "error", "data": {"message": "Invalid approval data"}}
            )
            return

        # Resolve the approval in shared state
        state = get_state()
        success = state.resolve_approval(approval_id, approved)

        if not success:
            await self.send_message(
                websocket,
                {"type": "error", "data": {"message": f"Approval {approval_id} not found"}}
            )
            return

        # Broadcast the resolution to all clients
        await self.broadcast({
            "type": "approval_resolved",
            "data": {
                "approvalId": approval_id,
                "approved": approved,
            }
        })


# Global WebSocket manager instance
ws_manager = WebSocketManager()


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint handler."""
    await ws_manager.connect(websocket)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            # Handle the message
            await ws_manager.handle_message(websocket, data)

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)
