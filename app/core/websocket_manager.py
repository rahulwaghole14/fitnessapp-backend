from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        # Store active connections by their connection ID
        self.active_connections: Dict[str, WebSocket] = {}
        # Store connection metadata (e.g., user info, connection time)
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self._connection_counter = 0

    async def connect(self, websocket: WebSocket, connection_id: str = None) -> str:
        """Accept and store a WebSocket connection."""
        await websocket.accept()
        
        # Generate unique connection ID if not provided
        if connection_id is None:
            connection_id = f"conn_{self._connection_counter}"
            self._connection_counter += 1
        
        # Store connection
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "connected_at": asyncio.get_event_loop().time(),
            "connection_id": connection_id
        }
        
        logger.info(f"WebSocket connection established: {connection_id}")
        return connection_id

    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        logger.info(f"WebSocket connection disconnected: {connection_id}")

    async def send_personal_message(self, message: dict, connection_id: str):
        """Send a message to a specific connection."""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message))
                logger.debug(f"Message sent to {connection_id}: {message}")
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                # Remove broken connection
                self.disconnect(connection_id)

    async def broadcast(self, message: dict):
        """Broadcast a message to all active connections."""
        if not self.active_connections:
            logger.debug("No active connections to broadcast to")
            return
        
        # Create a list of connections to remove if they fail
        failed_connections = []
        
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
                logger.debug(f"Broadcast message sent to {connection_id}: {message}")
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_id}: {e}")
                failed_connections.append(connection_id)
        
        # Remove failed connections
        for connection_id in failed_connections:
            self.disconnect(connection_id)

    async def broadcast_to_admins(self, message: dict):
        """Broadcast a message specifically to admin connections."""
        # For now, broadcast to all connections
        # In future, you can filter by connection metadata
        await self.broadcast(message)

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)

    def get_connection_info(self) -> List[Dict[str, Any]]:
        """Get information about all active connections."""
        return [
            {
                "connection_id": conn_id,
                **metadata
            }
            for conn_id, metadata in self.connection_metadata.items()
        ]


# Global instance for the application
websocket_manager = WebSocketManager()
