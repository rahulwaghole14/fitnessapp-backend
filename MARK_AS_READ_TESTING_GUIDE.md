# Mark as Read Functionality - Testing Guide

## Overview

The notification system now supports marking notifications as read, both individually and in bulk. This guide provides step-by-step instructions to test all the new features.

## Prerequisites

1. **Run Database Migration** (First time only):
   ```bash
   python migration_add_is_read_column.py
   ```

2. **Start Server**:
   ```bash
   uvicorn app.main:app --port 8000 --host 0.0.0.0 --reload
   ```

3. **Get Admin Token**:
   ```http
   POST /api/admin/login
   Content-Type: application/json
   
   {
       "email": "admin@test.com",
       "password": "admin123"
   }
   ```

---

## New API Endpoints

### 1. Mark Single Notification as Read
```http
POST /api/admin/notifications/{notification_id}/mark-read
Authorization: Bearer <admin_token>
```

### 2. Mark All Notifications as Read
```http
POST /api/admin/notifications/mark-all-read
Authorization: Bearer <admin_token>
```

### 3. Get Unread Count
```http
GET /api/admin/notifications/unread-count
Authorization: Bearer <admin_token>
```

---

## Testing Steps

### Step 1: Generate Test Notifications

Create some test notifications:

```http
POST /api/v1/register
Content-Type: application/json

{
    "username": "testuser1",
    "email": "test1@example.com",
    "password": "password123"
}
```

```http
POST /api/v1/register
Content-Type: application/json

{
    "username": "testuser2",
    "email": "test2@example.com",
    "password": "password123"
}
```

```http
POST /api/v1/register
Content-Type: application/json

{
    "username": "testuser3",
    "email": "test3@example.com",
    "password": "password123"
}
```

### Step 2: Check Initial Notification Status

```http
GET /api/admin/notifications?limit=10
Authorization: Bearer <admin_token>
```

**Expected Response** (all notifications should have `is_read: false`):
```json
[
    {
        "id": 3,
        "user_id": 3,
        "username": "testuser3",
        "activity_type": "USER_REGISTERED",
        "description": "testuser3 signed up",
        "is_read": false,
        "created_at": "2024-01-15T10:35:00Z",
        "time_ago": "just now",
        "is_admin_important": true
    },
    {
        "id": 2,
        "user_id": 2,
        "username": "testuser2",
        "activity_type": "USER_REGISTERED",
        "description": "testuser2 signed up",
        "is_read": false,
        "created_at": "2024-01-15T10:34:00Z",
        "time_ago": "1 min ago",
        "is_admin_important": true
    },
    {
        "id": 1,
        "user_id": 1,
        "username": "testuser1",
        "activity_type": "USER_REGISTERED",
        "description": "testuser1 signed up",
        "is_read": false,
        "created_at": "2024-01-15T10:33:00Z",
        "time_ago": "2 min ago",
        "is_admin_important": true
    }
]
```

### Step 3: Check Unread Count

```http
GET /api/admin/notifications/unread-count
Authorization: Bearer <admin_token>
```

**Expected Response**:
```json
{
    "unread_count": 3
}
```

### Step 4: Mark Single Notification as Read

```http
POST /api/admin/notifications/2/mark-read
Authorization: Bearer <admin_token>
```

**Expected Response**:
```json
{
    "message": "Notification marked as read successfully",
    "notification_id": 2,
    "is_read": true
}
```

### Step 5: Verify Single Mark as Read

```http
GET /api/admin/notifications?limit=10
Authorization: Bearer <admin_token>
```

**Expected Response** (notification ID 2 should now be marked as read):
```json
[
    {
        "id": 3,
        "user_id": 3,
        "username": "testuser3",
        "activity_type": "USER_REGISTERED",
        "description": "testuser3 signed up",
        "is_read": false,
        "created_at": "2024-01-15T10:35:00Z",
        "time_ago": "just now",
        "is_admin_important": true
    },
    {
        "id": 2,
        "user_id": 2,
        "username": "testuser2",
        "activity_type": "USER_REGISTERED",
        "description": "testuser2 signed up",
        "is_read": true,
        "created_at": "2024-01-15T10:34:00Z",
        "time_ago": "1 min ago",
        "is_admin_important": true
    },
    {
        "id": 1,
        "user_id": 1,
        "username": "testuser1",
        "activity_type": "USER_REGISTERED",
        "description": "testuser1 signed up",
        "is_read": false,
        "created_at": "2024-01-15T10:33:00Z",
        "time_ago": "2 min ago",
        "is_admin_important": true
    }
]
```

### Step 6: Check Updated Unread Count

```http
GET /api/admin/notifications/unread-count
Authorization: Bearer <admin_token>
```

**Expected Response**:
```json
{
    "unread_count": 2
}
```

### Step 7: Mark All Notifications as Read

```http
POST /api/admin/notifications/mark-all-read
Authorization: Bearer <admin_token>
```

**Expected Response**:
```json
{
    "message": "Successfully marked 2 notifications as read",
    "marked_count": 2,
    "activity_type_filter": null
}
```

### Step 8: Verify All Marked as Read

```http
GET /api/admin/notifications?limit=10
Authorization: Bearer <admin_token>
```

**Expected Response** (all notifications should have `is_read: true`):
```json
[
    {
        "id": 3,
        "user_id": 3,
        "username": "testuser3",
        "activity_type": "USER_REGISTERED",
        "description": "testuser3 signed up",
        "is_read": true,
        "created_at": "2024-01-15T10:35:00Z",
        "time_ago": "just now",
        "is_admin_important": true
    },
    {
        "id": 2,
        "user_id": 2,
        "username": "testuser2",
        "activity_type": "USER_REGISTERED",
        "description": "testuser2 signed up",
        "is_read": true,
        "created_at": "2024-01-15T10:34:00Z",
        "time_ago": "1 min ago",
        "is_admin_important": true
    },
    {
        "id": 1,
        "user_id": 1,
        "username": "testuser1",
        "activity_type": "USER_REGISTERED",
        "description": "testuser1 signed up",
        "is_read": true,
        "created_at": "2024-01-15T10:33:00Z",
        "time_ago": "2 min ago",
        "is_admin_important": true
    }
]
```

### Step 9: Check Final Unread Count

```http
GET /api/admin/notifications/unread-count
Authorization: Bearer <admin_token>
```

**Expected Response**:
```json
{
    "unread_count": 0
}
```

---

## Advanced Testing

### Test Mark All by Activity Type

```http
POST /api/admin/notifications/mark-all-read?activity_type=USER_REGISTERED
Authorization: Bearer <admin_token>
```

### Test Updated Statistics

```http
GET /api/admin/notifications/stats
Authorization: Bearer <admin_token>
```

**Expected Response** (includes read/unread breakdown):
```json
{
    "total_notifications": 3,
    "admin_notifications": 3,
    "admin_read": 3,
    "admin_unread": 0,
    "activity_counts": {
        "USER_REGISTERED": {
            "total": 3,
            "unread": 0,
            "read": 3
        },
        "FAILED_LOGIN": {
            "total": 0,
            "unread": 0,
            "read": 0
        }
        // ... other activity types
    },
    "active_connections": 1
}
```

---

## Error Testing

### Test Invalid Notification ID

```http
POST /api/admin/notifications/999/mark-read
Authorization: Bearer <admin_token>
```

**Expected Response**:
```json
{
    "detail": "Notification not found"
}
```

### Test Unauthorized Access

```http
POST /api/admin/notifications/1/mark-read
```

**Expected Response**:
```json
{
    "detail": "Not authenticated"
}
```

---

## WebSocket Integration Test

1. **Connect WebSocket**: `ws://localhost:8000/ws/admin/notifications`
2. **Register New User**: Creates new notification (unread)
3. **Mark as Read**: Use API to mark notification as read
4. **Verify**: WebSocket still receives new notifications, read status doesn't affect real-time delivery

---

## Database Verification

After testing, you can verify the database directly:

```sql
SELECT id, username, activity_type, is_read, created_at 
FROM activity_logs 
WHERE activity_type = 'USER_REGISTERED'
ORDER BY created_at DESC;
```

---

## Performance Testing

For large datasets, test the performance:

```bash
# Create many test notifications
for i in {1..100}; do
  curl -X POST http://localhost:8000/api/v1/register \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"testuser$i\",\"email\":\"test$i@example.com\",\"password\":\"password123\"}"
done

# Test mark all as read performance
time curl -X POST http://localhost:8000/api/admin/notifications/mark-all-read \
  -H "Authorization: Bearer <token>"
```

---

## Success Checklist

- [ ] Database migration runs successfully
- [ ] New notifications have `is_read: false`
- [ ] Single notification mark as read works
- [ ] All notifications mark as read works
- [ ] Unread count updates correctly
- [ ] Statistics include read/unread breakdown
- [ ] Activity type filtering works for bulk operations
- [ ] Error handling works for invalid IDs
- [ ] WebSocket notifications still work with read status
- [ ] Performance is acceptable with large datasets

---

## Troubleshooting

### Migration Issues
- Ensure PostgreSQL is running
- Check database connection in `.env`
- Run migration script manually if needed

### Performance Issues
- Check database indexes are created
- Monitor query execution time
- Consider pagination for large datasets

### Read Status Not Updating
- Verify `is_read` column exists
- Check database transaction commits
- Review API response codes

The mark as read functionality is now fully integrated and ready for production use!
