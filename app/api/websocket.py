from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.core.websocket_manager import websocket_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/admin/notifications")
async def websocket_admin_notifications(websocket: WebSocket):
    """
    WebSocket endpoint for real-time admin notifications.
    
    Admin dashboard should connect to: ws://localhost:8000/ws/admin/notifications
    """
    connection_id = None
    try:
        # Accept the WebSocket connection
        connection_id = await websocket_manager.connect(websocket)
        
        logger.info(f"Admin connected via WebSocket: {connection_id}")
        
        # Send a welcome message to confirm connection
        await websocket_manager.send_personal_message(
            {
                "type": "connection_established",
                "message": "Connected to admin notifications",
                "connection_id": connection_id,
                "timestamp": "now"
            },
            connection_id
        )
        
        # Keep the connection alive and listen for messages
        while True:
            try:
                # Wait for incoming messages (ping/pong or other commands)
                data = await websocket.receive_text()
                
                # Handle incoming messages if needed
                # For now, we'll just log them
                logger.debug(f"Received message from {connection_id}: {data}")
                
                # Echo back for testing (optional)
                await websocket_manager.send_personal_message(
                    {
                        "type": "echo",
                        "message": f"Received: {data}",
                        "timestamp": "now"
                    },
                    connection_id
                )
                
            except WebSocketDisconnect:
                logger.info(f"Admin WebSocket disconnected: {connection_id}")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket loop for {connection_id}: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"Admin WebSocket disconnected during handshake: {connection_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket endpoint: {e}")
    finally:
        # Clean up the connection
        if connection_id:
            websocket_manager.disconnect(connection_id)
