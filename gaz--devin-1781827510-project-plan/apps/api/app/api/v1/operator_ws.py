"""
Operator WebSocket — real-time notifications for the operator console.

When a conversation is escalated (via escalate_to_human tool), all connected
operators receive a push notification so they can pick up the conversation
without refreshing the page.
"""

import asyncio
import json
import logging
from collections.abc import MutableSet
from dataclasses import dataclass, field
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/operator", tags=["operator"])


@dataclass
class OperatorConnectionManager:
    """Manages active WebSocket connections from operator console clients."""

    # tenant_id -> set of WebSockets
    _connections: dict[str, MutableSet[WebSocket]] = field(default_factory=dict)

    async def connect(self, tenant_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if tenant_id not in self._connections:
            self._connections[tenant_id] = set()
        self._connections[tenant_id].add(websocket)
        logger.info("Operator connected to tenant %s. Total for tenant: %d", tenant_id, len(self._connections[tenant_id]))

    def disconnect(self, tenant_id: str, websocket: WebSocket) -> None:
        if tenant_id in self._connections:
            self._connections[tenant_id].discard(websocket)
            if not self._connections[tenant_id]:
                del self._connections[tenant_id]
            else:
                logger.info("Operator disconnected from tenant %s. Total for tenant: %d", tenant_id, len(self._connections[tenant_id]))

    async def broadcast_to_tenant(self, tenant_id: str, event: str, data: dict[str, object]) -> None:
        """Send an event to all connected operators for a specific tenant."""
        if tenant_id not in self._connections:
            return
            
        message = json.dumps({"event": event, "data": data})
        disconnected: list[WebSocket] = []
        for connection in self._connections[tenant_id]:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
                
        for ws in disconnected:
            self._connections[tenant_id].discard(ws)

    def count(self, tenant_id: str) -> int:
        return len(self._connections.get(tenant_id, set()))


# Global singleton — imported by orchestrator to broadcast escalations
operator_manager = OperatorConnectionManager()


@router.websocket("/ws")
async def operator_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for operator console real-time updates.
    Must be authenticated via cf_access_token cookie.
    """
    token = websocket.cookies.get("cf_access_token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        return

    from app.security import verify_access_token
    from app.settings import get_settings
    settings = get_settings()
    
    try:
        claims = verify_access_token(token, settings.access_token_secret)
        tenant_id = str(claims.tenant_id)
    except Exception as e:
        logger.warning("Operator WS Auth failed: %s", e)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return

    await operator_manager.connect(tenant_id, websocket)

    try:
        # Send initial connection confirmation
        await websocket.send_text(
            json.dumps({
                "event": "connected",
                "data": {"operators_online": operator_manager.count(tenant_id)},
            })
        )

        # Heartbeat + message receive loop
        while True:
            try:
                # Wait for client messages with a 30-second timeout for heartbeat
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                msg = json.loads(data)

                if msg.get("event") == "pong":
                    continue  # Client responded to heartbeat

                # Handle other client events (e.g., operator accepting a conversation)
                if msg.get("event") == "accept_conversation":
                    conversation_id = msg.get("data", {}).get("conversation_id")
                    if conversation_id:
                        await operator_manager.broadcast_to_tenant(
                            tenant_id,
                            "conversation_accepted",
                            {
                                "conversation_id": conversation_id,
                                "accepted_by": "operator",
                            },
                        )

            except TimeoutError:
                # Send heartbeat ping
                try:
                    await websocket.send_text(
                        json.dumps({"event": "heartbeat", "data": {}})
                    )
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("Operator WebSocket error: %s", e)
    finally:
        operator_manager.disconnect(tenant_id, websocket)


async def notify_escalation(
    conversation_id: str,
    tenant_id: str,
    agent_name: str,
    customer_text: str,
    summary: str | None = None,
) -> None:
    """
    Called by the orchestrator when escalate_to_human tool is invoked.
    Broadcasts to all connected operators for the given tenant.
    """
    await operator_manager.broadcast_to_tenant(
        tenant_id,
        "new_escalation",
        {
            "conversation_id": conversation_id,
            "tenant_id": tenant_id,
            "agent_name": agent_name,
            "customer_text": customer_text,
            "summary": summary or customer_text[:100],
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
