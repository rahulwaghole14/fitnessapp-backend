from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.core.websocket_manager import websocket_manager
from app.core.jwt_utils import decode_access_token
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


@router.websocket("/user/notifications")
async def websocket_user_notifications(websocket: WebSocket):
    """
    WebSocket endpoint for real-time user-specific notifications.
    
    User client should connect to: ws://localhost:8000/ws/user/notifications?token=ACCESS_TOKEN
    """
    token = websocket.query_params.get("token")
    if not token:
        logger.warning("Rejected User WebSocket connection: missing token query parameter.")
        await websocket.close(code=1008)  # WS_1008_POLICY_VIOLATION
        return

    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except Exception as e:
        logger.warning(f"Rejected User WebSocket connection: invalid token. Error: {e}")
        await websocket.close(code=3000)  # Custom close code for unauthorized
        return

    connection_id = None
    try:
        # Accept the WebSocket connection and register under user_id
        connection_id = await websocket_manager.connect_user(websocket, user_id)
        
        logger.info(f"User {user_id} connected via WebSocket: {connection_id}")
        
        # Send a welcome message to confirm connection
        await websocket_manager.send_personal_message(
            {
                "type": "connection_established",
                "message": "Connected to user notifications",
                "connection_id": connection_id,
                "user_id": user_id,
                "timestamp": "now"
            },
            connection_id
        )
        
        # Keep connection alive
        while True:
            try:
                # Listen for incoming messages (ping/pong)
                data = await websocket.receive_text()
                logger.debug(f"Received message from user connection {connection_id}: {data}")
                
                # Echo back message for testing
                await websocket_manager.send_personal_message(
                    {
                        "type": "echo",
                        "message": f"Received: {data}",
                        "timestamp": "now"
                    },
                    connection_id
                )
            except WebSocketDisconnect:
                logger.info(f"User WebSocket disconnected: {connection_id}")
                break
            except Exception as e:
                logger.error(f"Error in user WebSocket loop for {connection_id}: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"User WebSocket disconnected during handshake: {connection_id}")
    except Exception as e:
        logger.error(f"Error in user WebSocket endpoint: {e}")
    finally:
        # Clean up connection
        if connection_id:
            websocket_manager.disconnect_user(connection_id, user_id)

