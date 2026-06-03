# Real-Time Admin Notification System

## Overview

This implementation provides a real-time notification system for the FastAPI fitness application backend using WebSockets. Admin dashboard can receive instant notifications when important events occur in the system.

## Architecture

### Components

1. **WebSocket Connection Manager** (`app/core/websocket_manager.py`)
   - Manages active WebSocket connections
   - Handles connection/disconnection
   - Broadcasts messages to all connected admins

2. **Notification Service** (`app/services/notification_service.py`)
   - Contains business logic for notifications
   - Determines which activities are admin-important
   - Handles WebSocket message broadcasting

3. **WebSocket Endpoint** (`app/api/websocket.py`)
   - `/ws/admin/notifications` endpoint
   - Accepts WebSocket connections from admin dashboard
   - Maintains persistent connections

4. **REST API Endpoints** (`app/api/admin/notifications.py`)
   - `GET /admin/notifications` - Fetch past notifications
   - `GET /admin/notifications/stats` - Get notification statistics
   - `GET /admin/notifications/activity-types` - Get available activity types

5. **Enhanced Activity Logger** (`app/utils/activity_logger.py`)
   - Integrated with WebSocket notifications
   - Maps activity types to admin notification format
   - Automatically sends notifications for important events

## Features

### WebSocket Connection Management
- Thread-safe connection handling
- Automatic cleanup of disconnected clients
- Support for multiple admin connections
- Connection metadata tracking

### Notification Types
The system automatically sends notifications for these activity types:
- `USER_REGISTERED` - New user signup
- `FAILED_LOGIN` - Failed login attempts
- `SUBSCRIPTION_PURCHASED` - New subscription purchases
- `PROFILE_UPDATED` - User profile changes
- `PASSWORD_CHANGED` - Password changes
- `ACCOUNT_DEACTIVATED` - Account deactivation
- `PAYMENT_FAILED` - Payment failures
- `WORKOUT_COMPLETED` - Workout completions
- `GOAL_ACHIEVED` - Goal achievements
- `SUSPICIOUS_ACTIVITY` - Suspicious activities

### Message Format
```json
{
  "id": 123,
  "type": "USER_REGISTERED",
  "message": "John Doe signed up",
  "username": "johndoe",
  "timestamp": "2024-01-15T10:30:00Z",
  "user_id": 456
}
```

## API Endpoints

### WebSocket Connection
```
ws://localhost:8000/ws/admin/notifications
```

### REST Endpoints

#### Get Notifications
```http
GET /admin/notifications?limit=50&activity_type=USER_REGISTERED
```

#### Get Notification Statistics
```http
GET /admin/notifications/stats
```

#### Get Activity Types
```http
GET /admin/notifications/activity-types
```

## Integration

### Automatic Integration
The system is automatically integrated with existing activity logging:
- User registration (both admin and self-registration)
- Profile updates
- Any other activity using `log_activity()`

### Manual Integration
For new activities, use the notification service:

```python
from app.services.notification_service import notification_service

# Create activity and send notification
await notification_service.create_activity_and_notify(
    db=db,
    user_id=user.id,
    username=user.username,
    activity_type="CUSTOM_ACTIVITY",
    description="Custom activity description"
)
```

Or use the enhanced activity logger:

```python
from app.utils.activity_logger import log_activity

# Log activity with automatic notification
log_activity(
    db=db,
    user_id=user.id,
    username=user.username,
    activity_type="custom_activity",
    description="Custom activity description",
    send_notification=True
)
```

## Frontend Integration

### WebSocket Client (JavaScript)
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/admin/notifications');

ws.onopen = function(event) {
    console.log('Connected to admin notifications');
};

ws.onmessage = function(event) {
    const notification = JSON.parse(event.data);
    console.log('New notification:', notification);
    // Handle notification (show toast, update UI, etc.)
};

ws.onclose = function(event) {
    console.log('Disconnected from admin notifications');
    // Implement reconnection logic
};

ws.onerror = function(error) {
    console.error('WebSocket error:', error);
};
```

### Fetch Past Notifications
```javascript
// Fetch recent notifications
fetch('/admin/notifications?limit=50')
    .then(response => response.json())
    .then(notifications => {
        // Display notifications in admin dashboard
    });
```

## Testing

### WebSocket Test Script
Run the test script to verify WebSocket connectivity:

```bash
python test_websocket.py
```

### Manual Testing
1. Start the FastAPI server
2. Connect to WebSocket endpoint using test script or browser WebSocket client
3. Trigger activities (user registration, profile update, etc.)
4. Observe real-time notifications

## Configuration

### CORS Settings
WebSocket connections are already configured in `main.py`. Ensure your admin dashboard domain is included:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React Admin Dev
        "https://your-admin-domain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)
```

## Error Handling

- WebSocket failures don't affect API responses
- Notification errors are logged but don't break activity logging
- Automatic connection cleanup on disconnect
- Graceful handling of malformed messages

## Performance Considerations

- Async WebSocket operations don't block API responses
- Connection pooling for efficient resource usage
- Automatic cleanup of stale connections
- Efficient broadcasting to multiple clients

## Security

- WebSocket connections inherit existing authentication
- Admin-only endpoints for notification management
- Activity type filtering for relevant notifications
- No sensitive data in notification messages

## Monitoring

### Connection Status
```python
from app.core.websocket_manager import websocket_manager

# Get active connection count
connection_count = websocket_manager.get_connection_count()

# Get connection details
connections = websocket_manager.get_connection_info()
```

### Notification Statistics
Use the `/admin/notifications/stats` endpoint to get:
- Total notification count
- Admin-important notification count
- Activity type breakdown
- Active connection count

## Troubleshooting

### Common Issues

1. **WebSocket Connection Fails**
   - Check CORS settings
   - Verify server is running
   - Check firewall settings

2. **No Notifications Received**
   - Verify activity type is in `ADMIN_IMPORTANT_ACTIVITIES`
   - Check WebSocket connection is active
   - Review server logs for errors

3. **Performance Issues**
   - Monitor connection count
   - Check for memory leaks
   - Review notification frequency

### Debug Logging
Enable debug logging to troubleshoot:

```python
import logging
logging.getLogger('app.core.websocket_manager').setLevel(logging.DEBUG)
logging.getLogger('app.services.notification_service').setLevel(logging.DEBUG)
```

## Future Enhancements

- Notification persistence with `is_read` status
- User-specific notifications
- Notification templates
- Push notification integration
- Notification scheduling
- Advanced filtering and search
