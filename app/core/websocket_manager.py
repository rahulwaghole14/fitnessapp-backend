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
        # Maps user_id (int) -> List of connection IDs (str)
        self.user_connections: Dict[int, List[str]] = {}
        self._connection_counter = 0

    async def connect(self, websocket: WebSocket, connection_id: str = None) -> str:
        """Accept and store a WebSocket connection for admins."""
        await websocket.accept()
        
        # Generate unique connection ID if not provided
        if connection_id is None:
            connection_id = f"conn_{self._connection_counter}"
            self._connection_counter += 1
        
        # Store connection
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "connected_at": asyncio.get_event_loop().time(),
            "connection_id": connection_id,
            "role": "admin"
        }
        
        logger.info(f"Admin WebSocket connection established: {connection_id}")
        return connection_id

    async def connect_user(self, websocket: WebSocket, user_id: int) -> str:
        """Accept and store a WebSocket connection for a specific user."""
        await websocket.accept()
        
        connection_id = f"user_{user_id}_{self._connection_counter}"
        self._connection_counter += 1
        
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "connected_at": asyncio.get_event_loop().time(),
            "connection_id": connection_id,
            "role": "user",
            "user_id": user_id
        }
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(connection_id)
        
        # Update last_websocket_seen (Phase 5)
        try:
            from app.core.database import SessionLocal
            from app.models.user import User
            from datetime import datetime, timezone
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.last_websocket_seen = datetime.now(timezone.utc)
                    db.commit()
            finally:
                db.close()
        except Exception as db_err:
            logger.error(f"Failed to update last_websocket_seen for user {user_id}: {db_err}")

        logger.info(f"User {user_id} WebSocket connection established: {connection_id}")
        return connection_id

    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        logger.info(f"WebSocket connection disconnected: {connection_id}")

    def disconnect_user(self, connection_id: str, user_id: int):
        """Remove a user-specific WebSocket connection."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        if user_id in self.user_connections:
            if connection_id in self.user_connections[user_id]:
                self.user_connections[user_id].remove(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        logger.info(f"User {user_id} WebSocket connection disconnected: {connection_id}")

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
        admin_connections = {
            conn_id: self.active_connections[conn_id]
            for conn_id, meta in self.connection_metadata.items()
            if meta.get("role") == "admin" and conn_id in self.active_connections
        }
        
        if not admin_connections:
            return
            
        failed_connections = []
        for connection_id, websocket in admin_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to admin {connection_id}: {e}")
                failed_connections.append(connection_id)
                
        for connection_id in failed_connections:
            self.disconnect(connection_id)

    async def broadcast_event(self, event: str, data: dict):
        """
        Broadcast a standardized event to all connected admin clients.
        
        Args:
            event: Event type (e.g., "NOTIFICATION_READ", "ALL_NOTIFICATIONS_READ")
            data: Event data payload
        """
        # Find active admin connections
        admin_connections = {
            conn_id: self.active_connections[conn_id]
            for conn_id, meta in self.connection_metadata.items()
            if meta.get("role") == "admin" and conn_id in self.active_connections
        }
        
        if not admin_connections:
            logger.debug(f"No active admin connections to broadcast event: {event}")
            return
        
        # Create standardized event message
        event_message = {
            "event": event,
            "data": data
        }
        
        print(f"Broadcasting event: {event} to {len(admin_connections)} admin connections")
        logger.info(f"Broadcasting event: {event} to {len(admin_connections)} admin connections")
        
        # Create a list of connections to remove if they fail
        failed_connections = []
        
        for connection_id, websocket in admin_connections.items():
            try:
                await websocket.send_text(json.dumps(event_message))
                logger.debug(f"Event {event} sent to connection {connection_id}")
            except Exception as e:
                logger.error(f"Error broadcasting event {event} to {connection_id}: {e}")
                failed_connections.append(connection_id)
        
        # Remove failed connections
        for connection_id in failed_connections:
            self.disconnect(connection_id)
        
        print(f"Event {event} broadcast completed. Failed connections: {len(failed_connections)}")
        logger.info(f"Event {event} broadcast completed. Failed connections: {len(failed_connections)}")

    async def send_to_user(self, message: dict, user_id: int):
        """Send a message to all active WebSocket devices/sessions connected for the given user."""
        connection_ids = self.user_connections.get(user_id, [])
        if not connection_ids:
            logger.debug(f"No active WebSocket connections for user {user_id}")
            return
            
        failed_connections = []
        for connection_id in list(connection_ids):
            if connection_id in self.active_connections:
                websocket = self.active_connections[connection_id]
                try:
                    await websocket.send_text(json.dumps(message))
                    logger.debug(f"Message sent to user {user_id} connection {connection_id}: {message}")
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id} connection {connection_id}: {e}")
                    failed_connections.append(connection_id)
                    
        for connection_id in failed_connections:
            self.disconnect_user(connection_id, user_id)

    async def send_to_all_user_devices(self, user_id: int, event: str, data: dict):
        """Centralized real-time synchronization broadcaster per user."""
        event_message = {
            "event": event,
            "data": data
        }
        await self.send_to_user(event_message, user_id)

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
