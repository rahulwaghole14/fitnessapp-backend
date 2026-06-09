import asyncio
import websockets
import json

async def test_websocket_connection():
    """Test WebSocket connection to admin notifications endpoint."""
    uri = "ws://localhost:8000/ws/admin/notifications"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket!")
            
            # Listen for messages
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    print(f"Received notification: {data}")
                except websockets.exceptions.ConnectionClosed:
                    print("WebSocket connection closed")
                    break
                except Exception as e:
                    print(f"Error receiving message: {e}")
                    break
                    
    except Exception as e:
        print(f"Failed to connect to WebSocket: {e}")
        print("Make sure the FastAPI server is running on localhost:8000")

if __name__ == "__main__":
    print("Testing WebSocket connection...")
    print("Run this script while the FastAPI server is running")
    print("Then trigger some activity (like user registration) to see notifications")
    asyncio.run(test_websocket_connection())
