# Admin System Architecture - Fitness App

## 1. Admin System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ADMIN WEB CLIENT                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    ADMIN PANEL (React SPA)                      │   │
│  │                                                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │   Login     │  │   Users     │  │   Content  │             │   │
│  │  │   Page      │  │   Management│  │   Management│             │   │
│  │  │             │  │             │  │             │             │   │
│  │  │ • Email     │  │ • User List │  │ • Workouts  │             │   │
│  │  │ • Password  │  │ • Create    │  │ • Meals     │             │   │
│  │  │ • JWT Auth  │  │ • Update    │  │ • BMI       │             │   │
│  │  │             │  │ • Delete    │  │   Categories│             │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  │                                                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐                               │   │
│  │  │   Dashboard │  │   Settings  │                               │   │
│  │  │             │  │             │                               │   │
│  │  │ • Analytics │  │ • Profile   │                               │   │
│  │  │ • Stats     │  │ • Logout    │                               │   │
│  │  │ • Overview  │  │ • Token Mgmt│                               │   │
│  │  └─────────────┘  └─────────────┘                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ADMIN API ENDPOINT (/api/admin)                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    CORS MIDDLEWARE                              │   │
│  │                                                                 │   │
│  │  • Allow: http://localhost:3000 (Admin Panel)                  │   │
│  │  • Methods: GET, POST, PUT, DELETE, PATCH, OPTIONS           │   │
│  │  • Headers: *                                                  │   │
│  │  • Credentials: true                                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    ADMIN ROUTER                                 │   │
│  │                                                                 │   │
│  │  • /register     - Create admin account (only one allowed)     │   │
│  │  • /login        - Admin login with JWT                         │   │
│  │  • /refresh-token - Refresh JWT token                           │   │
│  │  • /logout       - Admin logout                                 │   │
│  │  • /users/*      - User management operations                   │   │
│  │  • /workouts/*   - Workout content management                   │   │
│  │  • /meals/*      - Meal content management                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        ADMIN BUSINESS LOGIC                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    AUTHENTICATION                                │   │
│  │                                                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │   Login      │  │   JWT       │  │   Token     │             │   │
│  │  │   Handler    │  │   Manager   │  │   Manager   │             │   │
│  │  │             │  │             │  │             │             │   │
│  │  │ • Verify     │  │ • Create    │  │ • Store     │             │   │
│  │  │   Password   │  │   Token     │  │   Hash      │             │   │
│  │  │ • Generate   │  │ • Validate  │  │ • Refresh   │             │   │
│  │  │   JWT        │  │ • Expire    │  │ • Revoke    │             │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    USER MANAGEMENT                                │   │
│  │                                                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │   User      │  │   User      │  │   User      │             │   │
│  │  │   CRUD      │  │   Profile   │  │   Media     │             │   │
│  │  │             │  │   Management│  │   Management│             │   │
│  │  │ • List Users│  │ • Update    │  │ • Upload    │             │   │
│  │  │ • Get User  │  │   Profile   │  │   Images    │             │   │
│  │  │ • Update    │  │ • BMI Data  │  │ • Validate  │             │   │
│  │  │ • Delete    │  │ • Activity  │  │   Files     │             │   │
│  │  │ • Create    │  │   Level     │  │             │             │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    CONTENT MANAGEMENT                            │   │
│  │                                                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │   Workout   │  │   Meal      │  │   BMI       │             │   │
│  │  │   Manager   │  │   Manager   │  │   Manager   │             │   │
│  │  │             │  │             │  │             │             │   │
│  │  │ • Create    │  │ • Create    │  │ • Create    │             │   │
│  │  │ • Edit      │  │ • Edit      │  │ • Update    │             │   │
│  │  │ • Delete    │  │ • Delete    │  │ • Delete    │             │   │
│  │  │ • List      │  │ • List      │  │ • List      │             │   │
│  │  │ • Media     │  │ • Category  │  │ • Validate  │             │   │
│  │  │   Upload    │  │   Based     │  │   Ranges    │             │   │
│  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           ADMIN DATA LAYER                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    DATABASE MODELS                               │   │
│  │                                                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │   Admin     │  │   User      │  │   Workout   │             │   │
│  │  │   Model     │  │   Model     │  │   Model     │             │   │
│  │  │             │  │             │  │             │             │   │
│  │  │ • id        │  │ • id        │  │ • id        │             │   │
│  │  │ • username  │  │ • username  │  │ • title     │             │   │
│  │  │ • email     │  │ • email     │  │ • description│             │   │
│  │  │ • password  │  │ • password  │  │ • duration  │             │   │
│  │  │ • is_active │  │ • is_verified│  │ • calorie  │             │   │
│  │  │ • created_at│  │ • bmi       │  │ • Level/Category│             │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  │                                                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │   Meal      │  │   BMI       │  │   Admin     │             │   │
│  │  │   Model     │  │   Class.    │  │   Refresh   │             │   │
│  │  │             │  │   Model     │  │   Token     │             │   │
│  │  │ • id        │  │ • id        │  │ • id        │             │   │
│  │  │ • bmi_cat_id│  │ • category  │  │ • admin_id  │             │   │
│  │  │ • meal_type │  │ • min_bmi   │  │ • token_hash│             │   │
│  │  │ • food_item │  │ • max_bmi   │  │ • jti       │             │   │
│  │  │ • calories  │  │ • created_at│  │ • expires_at│             │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    DATABASE CONNECTION                          │   │
│  │                                                                 │   │
│  │  • SQLAlchemy ORM                                               │   │
│  │  • Database (PostgreSQL)                                        │   │
│  │  • Session Management                                           │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## 2. Admin Request Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ADMIN REQUEST FLOW                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. ADMIN PANEL REQUEST                                                 │
│     ┌─────────────────────────────────────────────────────────────┐   │
│     │  React Admin Panel sends HTTP request                        │   │
│     │  • URL: /api/admin/endpoint                                   │   │
│     │  • Headers: Authorization: Bearer JWT Token                   │   │
│     │  • Method: GET/POST/PUT/DELETE                               │   │
│     │  • Body: JSON data or FormData (for file uploads)           │   │
│     └─────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│                                                                         │
│  2. CORS MIDDLEWARE                                                    │
│     ┌─────────────────────────────────────────────────────────────┐   │
│     │  Check if request is from allowed origin                      │   │
│     │  • Origin: http://localhost:3000 ✓                            │   │
│     │  • Credentials: true ✓                                        │   │
│     │  • Headers: Allowed ✓                                         │   │
│     │  • Methods: Allowed ✓                                         │   │
│     └─────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│                                                                         │
│  3. JWT AUTHENTICATION                                                 │
│     ┌─────────────────────────────────────────────────────────────┐   │
│     │  Validate JWT token from request header                      │   │
│     │  • Check token signature                                     │   │
│     │  • Verify token expiry                                       │   │
│     │  • Get admin user from database                              │   │
│     │  • Check if admin is active                                  │   │
│     │  • Validate admin permissions                                │   │
│     └─────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│                                                                         │
│  4. BUSINESS LOGIC                                                     │
│     ┌─────────────────────────────────────────────────────────────┐   │
│     │  Process the request based on endpoint                        │   │
│     │  • User Management: CRUD operations on users                  │   │
│     │  • Content Management: CRUD operations on workouts/meals     │   │
│     │  • Authentication: Login/logout/token refresh operations     │   │
│     │  • Media Handling: File uploads for workouts/profile images  │   │
│     │  • BMI Management: Category and meal management              │   │
│     └─────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│                                                                         │
│  5. DATABASE OPERATIONS                                                │
│     ┌─────────────────────────────────────────────────────────────┐   │
│     │  Execute database queries using SQLAlchemy                     │   │
│     │  • Create/Read/Update/Delete operations                       │   │
│     │  • Transaction management                                     │   │
│     │  • Data validation                                            │   │
│     │  • File system operations for media                           │   │
│     └─────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│                                                                         │
│  6. RESPONSE TO ADMIN PANEL                                            │
│     ┌─────────────────────────────────────────────────────────────┐   │
│     │  Send JSON response back to admin panel                       │   │
│     │  • Success: {data: {...}}                                    │   │
│     │  • Error: {detail: "message"}                               │   │
│     │  • Status codes: 200, 201, 400, 401, 403, 404, 500          │   │
│     └─────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 3. Admin API Endpoints

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ADMIN API ENDPOINTS                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    AUTHENTICATION                                │   │
│  │  • POST /api/admin/register        - Create new admin account  │   │
│  │  • POST /api/admin/login           - Admin login (returns JWT) │   │
│  │  • POST /api/admin/refresh-token   - Refresh JWT token         │   │
│  │  • POST /api/admin/logout          - Admin logout               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    USER MANAGEMENT                               │   │
│  │  • POST   /api/admin/register-user - Create new user            │   │
│  │  • GET    /api/admin/users         - Get all users (paginated) │   │
│  │  • GET    /api/admin/users/{id}    - Get specific user         │   │
│  │  • PUT    /api/admin/users/{id}    - Update user details       │   │
│  │  • DELETE /api/admin/users/{id}    - Delete user               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    WORKOUT MANAGEMENT                           │   │
│  │  • POST   /api/admin/workouts     - Create new workout         │   │
│  │  • GET    /api/admin/workouts     - Get all workouts           │   │
│  │  • GET    /api/admin/workouts/{id} - Get specific workout      │   │
│  │  • PUT    /api/admin/workouts/{id} - Update workout           │   │
│  │  • DELETE /api/admin/workouts/{id} - Delete workout           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    MEAL MANAGEMENT                               │   │
│  │  • POST   /api/admin/meals        - Create new meal             │   │
│  │  • GET    /api/admin/meals        - Get all meals               │   │
│  │  • GET    /api/admin/meals/{id}   - Get specific meal           │   │
│  │  • PUT    /api/admin/meals/{id}   - Update meal                 │   │
│  │  • DELETE /api/admin/meals/{id}   - Delete meal                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 4. Admin Security

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ADMIN SECURITY                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    AUTHENTICATION                                 │   │
│  │  • JWT Access Tokens (60 minutes expiry)                         │   │
│  │  • JWT Refresh Tokens (7 days expiry)                           │   │
│  │  • bcrypt for password hashing (72-byte limit)                  │   │
│  │  • Admin-specific secret key (ADMIN_SECRET_KEY)                 │   │
│  │  • Token hash storage for refresh tokens                         │   │
│  │  • Token revocation on logout                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    AUTHORIZATION                                  │   │
│  │  • Single admin system (only one admin allowed)                  │   │
│  │  • Full system access to all user data                          │   │
│  │  • Complete CRUD operations on all resources                     │   │
│  │  • Admin status validation (is_active check)                    │   │
│  │  • JWT-based session management                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    CORS CONFIGURATION                             │   │
│  │  • Only allows admin panel: http://localhost:3000               │   │
│  │  • Supports credentials (cookies, authorization headers)        │   │
│  │  • Allows all HTTP methods needed for admin operations          │   │
│  │  • Allows all headers for flexibility                           │   │
│  │  • Production domain support (configurable)                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 5. Data Models Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DATA MODELS                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    ADMIN MODEL                                   │   │
│  │  • id (Integer, Primary Key)                                    │   │
│  │  • username (String, Unique, Indexed)                           │   │
│  │  • email (String, Unique, Indexed)                             │   │
│  │  • password_hash (String, bcrypt hashed)                       │   │
│  │  • is_active (Boolean, Default: True)                          │   │
│  │  • created_at (DateTime)                                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    ADMIN REFRESH TOKEN                            │   │
│  │  • id (Integer, Primary Key)                                    │   │
│  │  • admin_id (Foreign Key to Admin)                              │   │
│  │  • token_hash (String, SHA256 hashed)                           │   │
│  │  • jti (String, JWT ID, Unique)                                 │   │
│  │  • expires_at (DateTime)                                         │   │
│  │  • is_revoked (Boolean, Default: False)                         │   │
│  │  • created_at (DateTime)                                        │   │
│  │  • last_used_at (DateTime)                                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    USER MODEL                                     │   │
│  │  • id (Integer, Primary Key)                                    │   │
│  │  • username (String, Unique, Indexed)                           │   │
│  │  • email (String, Unique, Indexed)                             │   │
│  │  • password (String, bcrypt hashed)                             │   │
│  │  • is_verified (Boolean, Default: False)                        │   │
│  │  • gender, age, weight, height, bmi (Optional)                 │   │
│  │  • weight_goal, activity_level (Optional)                       │   │
│  │  • profile_image (String, Optional)                             │   │
│  │  • otp, otp_created_at (For email verification)                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    WORKOUT MODEL                                  │   │
│  │  • id (Integer, Primary Key)                                    │   │
│  │  • title (String)                                               │   │
│  │  • description (String)                                          │   │
│  │  • workout_image_url (String)                                   │   │
│  │  • workout_video_url (String)                                   │   │
│  │  • duration (Integer, minutes)                                  │   │
│  │  • calorie_burn (Integer)                                        │   │
│  │  • activity_level (String: beginner/intermediate/advanced)     │   │
│  │  • workout_category (String: gain/loose/maintain)               │   │
│  │  • created_at, updated_at (DateTime)                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    MEAL MODEL                                     │   │
│  │  • id (Integer, Primary Key)                                    │   │
│  │  • bmi_category_id (Foreign Key to BMI Classification)          │   │
│  │  • meal_type (String: breakfast/lunch/dinner)                   │   │
│  │  • food_item (String)                                           │   │
│  │  • calories (Integer)                                            │   │
│  │  • created_at (DateTime)                                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    BMI CLASSIFICATION MODEL                       │   │
│  │  • id (Integer, Primary Key)                                    │   │
│  │  • category_name (String, Indexed)                              │   │
│  │  • min_bmi (Float, Optional)                                   │   │
│  │  • max_bmi (Float, Optional)                                   │   │
│  │  • created_at (DateTime)                                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 6. Technology Stack

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ADMIN MODULE TECHNOLOGY                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    FRONTEND                                       │   │
│  │  • React SPA (Single Page Application)                           │   │
│  │  • Runs on http://localhost:3000                                  │   │
│  │  • Communicates with backend via REST API                        │   │
│  │  • File upload support for media content                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    BACKEND                                       │   │
│  │  • FastAPI (Python web framework)                               │   │
│  │  • SQLAlchemy (ORM for database operations)                    │   │
│  │  • Pydantic (data validation and serialization)                │   │
│  │  • python-jose (JWT token handling)                            │   │
│  │  • bcrypt (password hashing)                                    │   │
│  │  • python-multipart (file upload support)                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    DATABASE                                      │   │
│  │  • PostgreSQL or MySQL (configurable)                          │   │
│  │  • Connection pooling                                            │   │
│  │  • Session management                                           │   │
│  │  • Migration support                                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    MEDIA STORAGE                                 │   │
│  │  • Local file system storage                                     │   │
│  │  • Organized media directories:                                  │   │
│  │  • - app/media/profile_images/                                   │   │
│  │  • - app/media/workout_images/                                   │   │
│  │  • - app/media/workout_videos/                                   │   │
│  │  • Static file serving via FastAPI                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 7. Key Features & Capabilities

### 7.1 Authentication & Authorization
- **Single Admin System**: Only one admin account allowed in the system
- **JWT-based Authentication**: Access tokens (60 min) + Refresh tokens (7 days)
- **Secure Password Hashing**: bcrypt with 72-byte limit
- **Token Management**: Secure storage, validation, and revocation
- **CORS Protection**: Restricted to admin frontend domain

### 7.2 User Management
- **Complete CRUD Operations**: Create, read, update, delete users
- **Profile Management**: Update user profiles, BMI data, activity levels
- **Media Upload**: Profile image management
- **User Registration**: Admin can create new user accounts

### 7.3 Content Management
- **Workout Management**: Create/edit/delete workouts with media support
- **Meal Management**: BMI category-based meal planning
- **BMI Classification**: Manage BMI categories and ranges
- **File Upload**: Support for workout images and videos

### 7.4 Security Features
- **Input Validation**: Pydantic schemas for all inputs
- **SQL Injection Protection**: SQLAlchemy ORM
- **XSS Protection**: FastAPI built-in protections
- **Secure File Upload**: File type validation and storage

## 8. File Structure

```
app/
├── api/
│   └── admin/
│       ├── __init__.py
│       ├── router.py          # Main admin router
│       ├── auth.py            # Authentication logic
│       ├── auth_tokens.py     # Token management
│       ├── dependencies.py    # JWT dependencies
│       ├── schemas.py         # Pydantic schemas
│       ├── users.py           # User management
│       ├── workouts.py        # Workout management
│       └── meals.py           # Meal management
├── models/
│   ├── admin.py              # Admin models
│   ├── user.py               # User model
│   ├── workout.py            # Workout model
│   ├── meal.py               # Meal model
│   └── bmi_classification.py # BMI classification model
├── core/
│   └── database.py           # Database configuration
├── services/
│   ├── image_service.py     # Image upload service
│   └── workout_media_service.py # Workout media service
└── media/                   # Static media files
    ├── profile_images/
    ├── workout_images/
    └── workout_videos/
```

## 9. Environment Configuration

```env
# Admin Configuration
ADMIN_SECRET_KEY=your-secret-key-here

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost/fitness_db

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,https://admin.yourdomain.com
```

This architecture provides a comprehensive, secure, and scalable admin system for the fitness application, with proper separation of concerns, security measures, and maintainable code structure.
