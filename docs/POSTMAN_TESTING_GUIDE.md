# 🧪 Updated Postman Testing Guide

## ✅ Issues Fixed

1. **Python 3.14 Compatibility**: Replaced `pytz` with `zoneinfo` for better compatibility
2. **WebSocket Routing**: Fixed WebSocket endpoint to be accessible at `/ws/admin/notifications`
3. **Import Errors**: Resolved all import and dependency issues

---

## 🚀 **Step 1: Start the Server**

```bash
cd d:\Fitness_App
uvicorn app.main:app --port 8000 --host 0.0.0.0 --reload
```

**Expected Output:**
```
INFO:     Will watch for changes in these directories: ['D:\\Fitness_App']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Application startup complete.
```

---

## 📡 **Step 2: Test WebSocket Connection**

### **Method A: Postman WebSocket (Recommended)**

1. **Open Postman**
2. **Create New WebSocket Request**:
   - Click `+` → Select `WebSocket`
   - Enter URL: `ws://localhost:8000/ws/admin/notifications`
   - Click `Connect`

3. **Expected Response**:
   ```json
   {
     "type": "connection_established",
     "message": "Connected to admin notifications",
     "connection_id": "conn_0",
     "timestamp": "now"
   }
   ```

### **Method B: Browser Console**

Open browser console (F12) and run:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/admin/notifications');
ws.onopen = () => console.log('Connected!');
ws.onmessage = (event) => console.log('Notification:', JSON.parse(event.data));
ws.onerror = (error) => console.error('WebSocket Error:', error);
```

---

## 📝 **Step 3: Test User Registration (Triggers Notification)**

### **Register New User**
```http
POST http://localhost:8000/api/v1/register
Content-Type: application/json

{
    "username": "testuser123",
    "email": "testuser123@example.com",
    "password": "password123"
}
```

**Expected WebSocket Message:**
```json
{
    "id": 1,
    "type": "USER_REGISTERED",
    "message": "testuser123 signed up",
    "username": "testuser123",
    "timestamp": "2024-01-15T10:30:00Z",
    "user_id": 1
}
```

---

## 👤 **Step 4: Test Admin Registration**

### **Register Admin User**
```http
POST http://localhost:8000/api/admin/register
Content-Type: application/json

{
    "username": "testadmin",
    "email": "admin@test.com",
    "password": "admin123"
}
```

### **Login as Admin**
```http
POST http://localhost:8000/api/admin/login
Content-Type: application/json

{
    "email": "admin@test.com",
    "password": "admin123"
}
```

### **Register User via Admin**
```http
POST http://localhost:8000/api/admin/register-user
Authorization: Bearer <admin_token>
Content-Type: application/json

{
    "username": "adminuser456",
    "email": "adminuser456@example.com",
    "password": "password123"
}
```

**Expected WebSocket Message:**
```json
{
    "id": 2,
    "type": "USER_REGISTERED",
    "message": "adminuser456 registered by admin",
    "username": "adminuser456",
    "timestamp": "2024-01-15T10:31:00Z",
    "user_id": 2
}
```

---

## 📊 **Step 5: Test Notification APIs**

### **Get Recent Notifications**
```http
GET http://localhost:8000/api/admin/notifications?limit=10
Authorization: Bearer <admin_token>
```

### **Get Notification Statistics**
```http
GET http://localhost:8000/api/admin/notifications/stats
Authorization: Bearer <admin_token>
```

### **Get Activity Types**
```http
GET http://localhost:8000/api/admin/notifications/activity-types
Authorization: Bearer <admin_token>
```

---

## 🧪 **Step 6: Test Multiple WebSocket Connections**

1. **Open Multiple Postman WebSocket Tabs**
2. **Connect all** to `ws://localhost:8000/ws/admin/notifications`
3. **Register a new user** - all connections should receive notification
4. **Verify** simultaneous message delivery

---

## 🔍 **Step 7: Verify Server Endpoints**

### **Check Server Status**
```http
GET http://localhost:8000/
```

**Expected Response:**
```json
{"message": "Fitness App API is running"}
```

### **Check Available Routes**
```http
GET http://localhost:8000/docs
```

This should show the FastAPI documentation with all endpoints including WebSocket.

---

## 🐛 **Troubleshooting**

### **WebSocket Connection Fails (404 Error)**
- ✅ **Fixed**: WebSocket routes now properly included at root level
- Verify server is running: `GET http://localhost:8000/`
- Check URL: Should be `ws://localhost:8000/ws/admin/notifications`

### **Import Errors**
- ✅ **Fixed**: Python 3.14 compatibility issues resolved
- ✅ **Fixed**: All import paths corrected

### **No Notifications Received**
1. Check WebSocket connection is active
2. Verify activity type is in `ADMIN_IMPORTANT_ACTIVITIES`
3. Check server logs for errors
4. Ensure user registration completes successfully

### **CORS Issues**
The server is configured to allow WebSocket connections from:
- `http://localhost:3000` (React Admin Dev)
- `https://fitness-app-dashboard-eight.vercel.app`

Add your domain if needed in `app/main.py`.

---

## ✅ **Success Indicators**

- [ ] Server starts without errors
- [ ] WebSocket connection established successfully
- [ ] User registration triggers real-time notification
- [ ] Multiple WebSocket clients receive notifications
- [ ] REST APIs return notification data
- [ ] Statistics show accurate counts

---

## 📊 **Expected Test Results**

After successful testing:
- **WebSocket Connection**: Established with connection message
- **User Registration**: Triggers instant notification to all connected clients
- **API Endpoints**: Return proper notification data and statistics
- **Multiple Clients**: All receive notifications simultaneously

The system is now fully functional and ready for integration with your admin dashboard!

---

## 📱 **Step 8: Test User In-App & Push Notifications (Upgraded System)**

### **Is Admin Notifications Still Working?**
**Yes, absolutely!** 
* The admin pipeline uses the `UserActivityLog` model and `activity_logs` table, which remain entirely unchanged.
* The admin WebSocket connection `/ws/admin/notifications` remains fully functional. 
* All admin REST APIs under `/api/admin/notifications` work exactly as they did before without any changes.

---

### **How to Test User In-App & Push Notifications in Postman**

#### **1. Authenticate to Get a User JWT Token**
If you don't have a user token, login or register a user:
```http
POST http://localhost:8000/api/v1/login
Content-Type: application/json

{
    "email": "sleeper@example.com",
    "password": "password123"
}
```
**Copy the `access_token`** from the response payload.

#### **2. Establish User WebSocket Connection in Postman**
1. Open a new **WebSocket Request** tab in Postman.
2. Enter the user WebSocket URL, appending your JWT token as a query parameter:
   ```
   ws://localhost:8000/ws/user/notifications?token=YOUR_JWT_ACCESS_TOKEN
   ```
3. Click **Connect**.
4. **Expected Output:**
   ```json
   {
     "type": "connection_established",
     "message": "Connected to user notifications",
     "connection_id": "user_30_0",
     "user_id": 30,
     "timestamp": "now"
   }
   ```

#### **3. Trigger a User Event (e.g., Sleep Analysis)**
Keep the WebSocket connection open and create a sleep session using the active user token:
```http
POST http://localhost:8000/api/v1/sleep/session
Authorization: Bearer YOUR_JWT_ACCESS_TOKEN
Content-Type: application/json

{
    "id": "e4b9db5e-3d23-41e9-91f8-9a3b2bce4b60",
    "startTime": "2026-06-01T22:30:00Z",
    "endTime": "2026-06-02T06:00:00Z",
    "isNap": false,
    "timezone": "Asia/Kolkata",
    "source": "wearable",
    "stages": {
        "awakeMinutes": 20,
        "lightMinutes": 280,
        "deepMinutes": 90,
        "remMinutes": 60
    }
}
```

##### **Expected Real-Time Responses:**
1. **User WebSocket Console** (Instant `NEW_NOTIFICATION` message with unread count):
   ```json
   {
     "event": "NEW_NOTIFICATION",
     "data": {
       "id": 1,
       "user_id": 30,
       "title": "Sleep Analysis Completed",
       "message": "Your sleep session on 2026-06-02 has been analyzed. You got a sleep score of 80 (Good)!",
       "notification_type": "SLEEP_ANALYSIS",
       "priority": "normal",
       "is_read": false,
       "is_deleted": false,
       "metadata": {
         "sleep_session_id": "e4b9db5e-3d23-41e9-91f8-9a3b2bce4b60",
         "sleep_score": 80,
         "sleep_quality": "Good",
         "wake_date": "2026-06-02"
       },
       "created_at": "2026-06-01T10:10:00.123456",
       "read_at": null,
       "unread_count": 1
     }
   }
   ```
2. **Server Logs** (Future-ready Push service logs stub execution):
   ```
   [INFO] [PUSH STUB] Queued push notification for User 30: 'Sleep Analysis Completed' - message: 'Your sleep session on 2026-06-02 has been analyzed. You got a sleep score of 80 (Good)!' | metadata: {...}
   ```

#### **4. Test User REST Notification APIs**

##### **A. Get All In-App Notifications**
* **Request**: `GET http://localhost:8000/api/v1/notifications?include_read=true`
* **Headers**: `Authorization: Bearer YOUR_JWT_ACCESS_TOKEN`
* **Expected Output**: Returns the active notifications list, total items, and global `unread_count`.

##### **B. Get Global Unread Count**
* **Request**: `GET http://localhost:8000/api/v1/notifications/unread-count`
* **Headers**: `Authorization: Bearer YOUR_JWT_ACCESS_TOKEN`
* **Expected Output**: `{ "unread_count": 1 }`

##### **C. Mark Notification as Read**
* **Request**: `PUT http://localhost:8000/api/v1/notifications/1/read`
* **Headers**: `Authorization: Bearer YOUR_JWT_ACCESS_TOKEN`
* **Expected Output**: `{ "message": "...", "notification_id": 1, "is_read": true }`
* **Real-Time Check**: Your open User WebSocket connection receives a `NOTIFICATION_READ` sync update:
  ```json
  {
    "event": "NOTIFICATION_READ",
    "data": {
      "id": 1,
      "is_read": true,
      "unread_count": 0
    }
  }
  ```

##### **D. Mark All Notifications as Read**
* **Request**: `PUT http://localhost:8000/api/v1/notifications/mark-all-read`
* **Headers**: `Authorization: Bearer YOUR_JWT_ACCESS_TOKEN`
* **Expected Output**: `{ "message": "...", "success": true }`
* **Real-Time Check**: WebSocket receives an `ALL_NOTIFICATIONS_READ` sync frame:
  ```json
  {
     "event": "ALL_NOTIFICATIONS_READ",
     "data": { "unread_count": 0 }
  }
  ```

##### **E. Delete a Notification**
* **Request**: `DELETE http://localhost:8000/api/v1/notifications/1`
* **Headers**: `Authorization: Bearer YOUR_JWT_ACCESS_TOKEN`
* **Expected Output**: `{ "message": "...", "success": true }`
* **Real-Time Check**: WebSocket receives a `NOTIFICATION_DELETED` sync frame:
  ```json
  {
     "event": "NOTIFICATION_DELETED",
     "data": { "id": 1, "unread_count": 0 }
  }
  ```

