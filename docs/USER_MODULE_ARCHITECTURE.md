# User Module Architecture - Fitness Tracking API

## 1. User Module Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MOBILE APP CLIENT                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        FITNESS MOBILE APP                                │   │
│  │                                                                         │   │
│  │ • User Registration & Login                                             │   │
│  │ • Activity Tracking (Workouts, Meals)                                   │   │
│  │ • Profile Management                                                    │   │
│  │ • Progress Analytics                                                    │   │
│  │ • BMI & Health Monitoring                                               │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        USER API GATEWAY (/api/v1)                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │   FastAPI App   │  │  Request Router │  │  File Upload   │              │
│  │                 │  │                 │  │                 │              │
│  │ • Main Entry    │  │ • Route to v1   │  • Profile Images│              │
│  │ • App Config   │  │ • Path Matching │  • Workout Media │              │
│  │ • Health Checks│  │ • Method Check │  • File Storage  │              │
│  │ • JWT Auth     │  │ • Versioning    │  • Media Serving │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        USER MODULE CORE                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    USER AUTHENTICATION                                     │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │   │
│  │  │   Registration  │  │      Login      │  │  Profile Mgmt   │        │   │
│  │  │                 │  │                 │  │                 │        │   │
│  │  │ • Email + Pass  │  │ • JWT Tokens    │  │ • Update Profile│        │   │
│  │  │ • Account Create│  │ • Access Token  │  │ • Profile Image │        │   │
│  │  │ • Password Hash │  │ • Refresh Token │  │ • Personal Info │        │   │
│  │  │ • Direct Login  │  │ • Session Mgmt  │  │ • Settings      │        │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        │   │
│  │                                                                                 │
│  │  ┌─────────────────┐  ┌─────────────────┐                                   │   │
│  │  │  Password Reset │  │  Token Refresh  │                                   │   │
│  │  │                 │  │                 │                                   │   │
│  │  │ • Forgot Password│  │ • Refresh Access │                                   │   │
│  │  │ • OTP Verify    │  │ • Token Expiry  │                                   │   │
│  │  │ • New Password  │  │ • Token Validation│                                  │   │
│  │  └─────────────────┘  └─────────────────┘                                   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                   USER ACTIVITY TRACKING                                  │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │   │
│  │  │ Daily Activities│  │ Weekly Stats    │  │ Monthly Reports │        │   │
│  │  │                 │  │                 │  │                 │        │   │
│  │  │ • Activity date │  │ • Week Summary  │  │ • Month Summary │        │   │
│  │  │ • Steps         │  │ • Total Steps   │  │ • Monthly steps │        │   │
│  │  │ • Duration      │  │ • Total Calories│  │ • calories     │        │   │
│  │  │ • Calories      │  │ • TotalDistance │  │ • distance      │        │   │
│  │  │ • Distance      │  │ • Total Duration│  │ • duration      │        │   │
│  │  │ • Date Tracking │  │ • Week          │  │ • Month         │        │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                 USER FITNESS & NUTRITION                                │   │
│  │  ┌─────────────────┐  ┌─────────────────┐                              │   │
│  │  │   Workouts      │  │      Meals      │                             │   │
│  │  │                 │  │                 │                             │   │
│  │  │ • Workout Media │  │ • id            │                             │   │
│  │  │ • Title         │  │ • bmi category  │                             │   │
│  │  │ • Calories      │  │ • Calories      │                             │   │
│  │  │ • Duration      │  │ • Meal          │                             │   │
│  │  │ • Level         │  │ • Meal Types    │                             │   │
│  │  └─────────────────┘  └─────────────────┘                             │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         USER DATA LAYER                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      USER DATA MODELS                                    │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │   │
│  │  │     User        │  │ Daily Activity  │  │ Monthly Activity│        │   │
│  │  │                 │  │                 │  │                 │        │   │
│  │  │ • id (PK)       │  │ • id (PK)       │  │ • id (PK)       │        │   │
│  │  │ • email (UK)    │  │ • user_id (FK)  │  │ • user_id (FK)  │        │   │
│  │  │ • username (UK) │  │ • activity_type │  │ • month         │        │   │
│  │  │ • password_hash │  │ • duration      │  │ • year          │        │   │
│  │  │ • otp           │  │ • calories      │  │ • total_count   │        │   │
│  │  │ • otp_created_at │  │ • distance      │  │ • total_calories│        │   │
│  │  │ • is_verified   │  │ • date          │  │ • total_duration│        │   │
│  │  │ • gender        │  │ • created_at    │  │ • created_at    │        │   │
│  │  │ • age           │  └─────────────────┘  └─────────────────┘        │   │
│  │  │ • weight        │                                                 │   │
│  │  │ • height        │                                                 │   │
│  │  │ • bmi           │                                                 │   │
│  │  │ • weight_goal   │                                                 │   │
│  │  │ • activity_level│                                                 │   │
│  │  │ • profile_image │                                                 │   │
│  │  └─────────────────┘                                                 │   │
│  │                                                                                 │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │   │
│  │  │ Refresh Token   │  │BMI Classification│  │ Workout Plans   │        │   │
│  │  │                 │  │                 │  │                 │        │   │
│  │  │ • id (PK)       │  │ • id (PK)       │  │ • id (PK)       │        │   │
│  │  │ • user_id (FK)  │  │ • category_name │  │ • Title         │        │   │
│  │  │ • token_hash    │  │ • min_bmi       │  │ • workouts desc │        │   │
│  │  │ • jti (UK)      │  │ • max_bmi       │  │ • calories      │        │   │
│  │  │ • expires_at    │  │ • description   │  │ • Level         │        │   │
│  │  │ • is_revoked    │  │                 │  │ • duration      │        │   │
│  │  │ • last_used_at  │  │                 │  │ • Workout media │        │   │
│  │  │ • created_at    │  │                 │  │ • Category      │        │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    USER DATA SCHEMAS                                      │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │   │
│  │  │  Auth Schemas   │  │ Activity Schemas│  │ Profile Schemas │        │   │
│  │  │                 │  │                 │  │                 │        │   │
│  │  │ • Register Req  │  │ • Activity Req  │  │ • Profile Update│        │   │
│  │  │ • Login Req     │  │ • Activity Res  │  │ • Profile Res   │        │   │
│  │  │ • OTP Verify    │  │ • Weekly Res    │  │ • Image Upload  │        │   │
│  │  │ • Password Reset│  │ • Monthly Res   │  │ • Settings      │        │   │
│  │  │ • Token Res     │  │                 │  │ • User Info     │        │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 2. Simple Request Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        APP REQUEST FLOW                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  MOBILE APP REQUEST                                                             │
│  ┌─────────────────┐                                                          │
│  │ API Request     │                                                          │
│  │ • JWT Token     │                                                          │
│  │ • User Data     │                                                          │
│  │ • Endpoint      │                                                          │
│  │ • Body          │                                                          │
│  └─────────┬───────┘                                                          │
│            │                                                                  │
│            ▼                                                                  │
│  ┌─────────────────┐                                                          │
│  │ FASTAPI ROUTER  │                                                          │
│  │                 │                                                          │
│  │ • Route Match   │                                                          │
│  │ • Auth Check    │                                                          │
│  │ • User Validate │                                                          │
│  └─────────┬───────┘                                                          │
│            │                                                                  │
│            ▼                                                                  │
│  ┌─────────────────┐                                                          │
│  │ BUSINESS LOGIC │                                                          │
│  │                 │                                                          │
│  │ • Process Data  │                                                          │
│  │ • Database Ops  │                                                          │
│  │ • Validation   │                                                          │
│  └─────────┬───────┘                                                          │
│            │                                                                  │
│            ▼                                                                  │
│  ┌─────────────────┐                                                          │
│  │ RESPONSE        │                                                          │
│  │                 │                                                          │
│  │ • JSON Data     │                                                          │
│  │ • Status Code   │                                                          │
│  │ • Error Handling│                                                          │
│  └─────────────────┘                                                          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 3. Simple Security Model

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         USER SECURITY                                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    AUTHENTICATION                                        │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │   │
│  │  │   Registration  │  │      Login      │  │  Token Mgmt     │        │   │
│  │  │                 │  │                 │  │                 │        │   │
│  │  │ • Email + Pass  │  │ • JWT Access    │  │ • Access Token  │        │   │
│  │  │ • Password Hash │  │ • JWT Refresh   │  │ • Refresh Token │        │   │
│  │  │ • Direct Login  │  │ • Session Mgmt  │  │ • Token Expiry  │        │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    AUTHORIZATION                                          │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │   │
│  │  │  Data Access   │  │  Resource Check │  │  Permission     │        │   │
│  │  │                 │  │                 │  │                 │        │   │
│  │  │ • Own Data Only │  │ • User Resources│  │ • Read Own      │        │   │
│  │  │ • User Context  │  │ • Activity Data │  │ • Write Own     │        │   │
│  │  │ • Session Bound │  │ • Profile Data  │  │ • Update Own    │        │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    DATA PROTECTION                                        │   │
│  │  ┌─────────────────┐  ┌─────────────────┐                                │   │
│  │  │  Input Security│  │  Output Security │                               |   │
│  │  │                 │  │                 │                               │   │
│  │  │ • Input Validation│  │ • Data Filtering │                            │   │
│  │  │ • SQL Injection │  │ • Safe Response │                               │   │
│  │  │ • Password Hash │  │ • Error Handling│                               │   │
│  │  └─────────────────┘  └─────────────────┘                               │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 4. API Endpoints

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         USER API ENDPOINTS (/api/v1)                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    AUTHENTICATION ENDPOINTS                               │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │   │
│  │  │ POST /register │  │ POST /login     │  │ PUT /setup-profile│        │   │
│  │  │                 │  │                 │  │                 │        │   │
│  │  │ • Email Input   │  │ • Credentials   │  │ • Profile Data  │        │   │
│  │  │ • User Creation │  │ • JWT Response  │  │ • Personal Info │        │   │
│  │  │ • Password Hash │  │ • Session Start │  │ • Fitness Data  │        │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        │   │
│  │                                                                                 │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │   │
│  │  │ POST /forgot-*  │  │ POST /auth/refresh│ │ GET /profile    │        │   │
│  │  │                 │  │                 │  │                 │        │   │
│  │  │ • Password Reset│  │ • Token Refresh │  │ • User Profile  │        │   │
│  │  │ • OTP Recovery  │  │ • New Access    │  │ • Profile Data  │        │   │
│  │  │ • Security      │  │ • Session Mgmt  │  │ • Personal Info │        │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    ACTIVITY ENDPOINTS                                      │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │   │
│  │  │ POST /activity/ │  │ GET /activity/* │  │ POST /activity/ │        │   │
│  │  │ daily           │  │                 │  │ monthly         │        │   │
│  │  │                 │  │                 │  │                 │        │   │
│  │  │ • Log Activity  │  │ • Daily Data    │  │ • Monthly Data  │        │   │
│  │  │ • Auto Calculate│  │ • Weekly Stats  │  │ • Archive Data  │        │   │
│  │  │ • Real-time     │  │ • Monthly Data  │  │ • Data Cleanup  │        │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    CONTENT ENDPOINTS                                       │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │   │
│  │  │ GET /workouts   │  │ POST /workouts   │  │ GET /meals      │        │   │
│  │  │                 │  │                 │  │                 │        │   │
│  │  │ • User Workouts │  │ • Create Workout│  │ • User Meals    │        │   │
│  │  │ • Personal Plans│  │ • Custom Plans  │  │ • Meal Plans    │        │   │
│  │  │ • Progress      │  │ • Exercise Log  │  │ • Nutrition     │        │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 5. Technology Stack

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        USER MODULE TECHNOLOGY                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      CORE FRAMEWORK                                       │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │   │
│  │  │   FastAPI       │  │   SQLAlchemy    │  │   Pydantic      │        │   │
│  │  │                 │  │                 │  │                 │        │   │
│  │  │ • Web Framework │  │ • ORM           │  │ • Data Validation│       │   │
│  │  │ • Async Support │  │ • Database Ops  │  │ • Serialization │        │   │
│  │  │ • Auto Docs     │  │ • Models        │  │ • Type Hints    │        │   │
│  │  │ • JWT Auth      │  │ • Relationships │  │ • Schemas       │        │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      AUTHENTICATION & SECURITY                           │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │   │
│  │  │   JWT (jose)    │  │   bcrypt        │  │   Email Service │        │   │
│  │  │                 │  │                 │  │                 │        │   │
│  │  │ • Token Creation│  │ • Password Hash │  │ • OTP Emails    │        │   │
│  │  │ • Token Validate│  │ • Password Verify│ │                 │        │   │
│  │  │ • Token Refresh │  │ • Security      │  │ • Templates     │        │   │
│  │  │ • Expiry Mgmt   │  │ • Salt Generation│ │ • Email Service │        │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      DATABASE & STORAGE                                   │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │   │
│  │  │   Database      │  │   File Storage  │  │   Environment   │        │   │
│  │  │                 │  │                 │  │                 │        │   │
│  │  │ • PostgreSQL    │  │ • Local Files   │  │ • .env Config   │        │   │
│  │  │                 │  │ • Media Files   │  │ • Secret Keys   │        │   │
│  │  │                 │  │ • Profile Images│  │ • Database URL  │        │   │
│  │  │                 │  │ • Uploads       │  │ • JWT Secrets   │        │   │
│  │  │                 │  │ • Media Serving │  │ • Email Config  │        │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 6. Architecture Flow Diagrams
### 6.1 User Registration Flow
```
┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Client  │───▶│ /register   │───▶│ Validation  │───▶│ Database    │
│ Request │    │ Endpoint    │    │ Service     │    │ Storage     │
└─────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                      │                    │                    │
                      ▼                    ▼                    ▼
               ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
               │ Hash         │    │ Email       │    │ User Record │
               │ Password     │    │ Validation  │    │ Created     │
               └─────────────┘    └─────────────┘    └─────────────┘
                      │                    │                    │
                      └────────────────────┼────────────────────┘
                                           ▼
                                    ┌─────────────┐
                                    │ Success     │
                                    │ Response    │
                                    └─────────────┘
```

### 6.2 User Authentication Flow
```
┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Client  │───▶│ /login      │───▶│ Credential  │───▶│ Database    │
│ Login   │    │ Endpoint    │    │ Validation  │    │ User Check  │
└─────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                      │                    │                    │
                      ▼                    ▼                    ▼
               ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
               │ Password    │    │ JWT Token   │    │ Refresh     │
               │ Verify      │    │ Generation  │    │ Token Store │
               └─────────────┘    └─────────────┘    └─────────────┘
                      │                    │                    │
                      └────────────────────┼────────────────────┘
                                           ▼
                                    ┌─────────────┐
                                    │ Token       │
                                    │ Response    │
                                    └─────────────┘
```

### 6.3 Profile Management Flow
```
┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Client  │───▶│ Auth        │───▶│ Profile     │───▶│ Database    │
│ Profile │    │ Middleware  │    │ Update      │    │ Update      │
│ Update  │    │             │    │ Service     │    │             │
└─────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                      │                    │                    │
                      ▼                    ▼                    ▼
               ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
               │ Image       │    │ Data        │    │ User Record │
               │ Upload      │    │ Validation  │    │ Updated     │
               └─────────────┘    └─────────────┘    └─────────────┘
                      │                    │                    │
                      └────────────────────┼────────────────────┘
                                           ▼
                                    ┌─────────────┐
                                    │ Updated     │
                                    │ Profile     │
                                    │ Response    │
                                    └─────────────┘
```

### 6.4 Password Reset Flow
```
┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Client  │───▶│ Send OTP    │───▶│ Generate    │───▶│ Email       │
│ Forgot  │    │ Request     │    │ OTP         │    │ Service     │
│ Password│    │             │    │             │    │             │
└─────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                      │                    │                    │
                      ▼                    ▼                    ▼
               ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
               │ Verify OTP  │───▶│ OTP         │───▶│ Reset       │
               │ Request     │    │ Validation  │    │ Password    │
               └─────────────┘    └─────────────┘    └─────────────┘
                      │                    │                    │
                      └────────────────────┼────────────────────┘
                                           ▼
                                    ┌─────────────┐
                                    │ Password    │
                                    │ Reset       │
                                    │ Complete    │
                                    └─────────────┘
```

## 7. Key Features & Implementation Details

### 7.1 User Authentication Features
- **Direct Registration**: Email + Username + Password (no OTP verification)
- **JWT Token System**: Access token (15min) + Refresh token (7days)
- **Password Security**: bcrypt hashing with salt
- **Session Management**: Token rotation and revocation support
- **Password Reset**: OTP-based recovery system

### 7.2 Profile Management Features
- **Fitness Profile**: Gender, Age, Weight, Height, BMI, Activity Level
- **Goal Setting**: Weight goals and activity preferences
- **Profile Images**: Upload and management with validation
- **Data Privacy**: User-specific data access control

### 7.3 Security Implementation
- **Input Validation**: Pydantic schemas for all inputs
- **SQL Injection Protection**: SQLAlchemy ORM usage
- **Token Security**: JTI-based token tracking and rotation
- **Image Security**: File type and size validation
- **Password Security**: bcrypt with backward compatibility

## 8. Database Relationships

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│      USER       │         │ DAILY ACTIVITY  │         │ MONTHLY ACTIVITY│
│                 │ 1:N     │                 │ 1:N     │                 │
│ • id (PK)       │◄────────│ • user_id (FK)  │◄────────│ • user_id (FK)  │
│ • email (UK)    │         │ • activity_type │         │ • month         │
│ • username (UK) │         │ • duration      │         │ • year          │
│ • password_hash │         │ • calories      │         │ • total_count   │
│ • profile_data  │         │ • date          │         │ • total_calories│
└─────────────────┘         └─────────────────┘         └─────────────────┘
         │                                                           │
         │ 1:N                         |-----------------------------|                              
         ▼                             ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│ REFRESH TOKEN   │         │ YEARLY ACTIVITY │         │ WORKOUT PLANS  │
│                 │         │                 │         │                 │
│ • id (PK)       │         │ • user_id (FK)  │         │ • user_id (FK)  │
│ • user_id (FK)  │         │ • year          │         │ • plan_name     │
│ • token_hash    │         │ • total_count   │         │ • exercises     │
│ • jti (UK)      │         │ • total_calories│         │ • difficulty    │
│ • expires_at    │         └─────────────────┘         └─────────────────┘
└─────────────────┘
```

## 9. File Structure

```
app/
├── models/
│   ├── user.py              # User model with fitness data
│   └── refresh_token.py     # JWT refresh token model
├── api/
│   ├── v1/
│   │   ├── auth.py          # User authentication endpoints
│   │   ├── auth_tokens.py   # Token management endpoints
│   │   └── router.py        # Route definitions
│   └── admin/
│       └── users.py         # Admin user management
├── schemas/
│   └── auth.py              # Authentication & profile schemas
├── core/
│   └── auth_dependencies.py # Authentication middleware
└── services/
    └── image_service.py     # Profile image handling
```

This architecture provides a comprehensive, secure, and scalable user management system specifically designed for your fitness tracking application, with all components based on your actual implementation.
