from fastapi import APIRouter
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.admin import Admin
from .schemas import (
    AdminRegister, AdminLogin, AdminResponse, TokenResponse,
    AdminForgotPasswordEmailSchema, AdminForgotPasswordVerifySchema, AdminForgotPasswordResetSchema, AdminChangePasswordSchema, AdminProfileUpdateSchema,
    UserRegisterSchema, UserRegisterResponse, UserResponse, UserUpdate, UserBlockResponse,
    WorkoutResponse, WorkoutCreate, WorkoutUpdate,
    MealResponse, MealCreate, MealUpdate,
    BMIClassificationResponse, BMIClassificationCreate, BMIClassificationUpdate,
    PaginatedResponse, PaginationInfo, AdminRefreshTokenRequest, AdminLogoutRequest, AdminRefreshTokenResponse,
    Plan, PlanCreate, PlanUpdate, UserSubscriptionResponse,
    OverviewResponse, UserResponsedash
)
from .auth import register_admin, login_admin, admin_forgot_password_send_otp, admin_forgot_password_verify_otp, admin_forgot_password_reset, admin_change_password, get_admin_profile, update_admin_profile
from .auth_tokens import refresh_admin_access_token, logout_admin
from .dashboard import get_overview, get_all_users
from .users import (
    register_user, get_users_paginated, get_user_by_id, update_user, delete_user
)
from .workouts import (
    create_workout, get_workouts_paginated, get_workout_by_id, update_workout, delete_workout
)
from .meals import (
    create_meal, get_meals_paginated, get_meal_by_id, update_meal, delete_meal
)
from .bmi_classification import (
    create_bmi_classification, get_bmi_classifications_paginated, get_bmi_classification_by_id, 
    update_bmi_classification, delete_bmi_classification
)
from .subscription_plans import create_plan, get_plans, get_plan_by_id, update_plan, delete_plan
from .users import get_user_subscriptions_paginated, get_user_subscription_by_id, update_user_subscription
from .activities import get_recent_activities
from .notifications import get_notifications, get_notification_stats, get_activity_types, mark_notification_as_read, mark_all_notifications_as_read, get_unread_notifications_count


admin_router = APIRouter()

# Admin Authentication Routes
admin_router.post("/register", response_model=AdminResponse)(register_admin)
admin_router.post("/login", response_model=TokenResponse)(login_admin)
admin_router.post("/refresh-token", response_model=AdminRefreshTokenResponse)(refresh_admin_access_token)
admin_router.post("/logout", response_model=None)(logout_admin)

# Admin Forgot Password Routes
admin_router.post("/auth/forgot-password/send")(admin_forgot_password_send_otp)
admin_router.post("/auth/forgot-password/verify")(admin_forgot_password_verify_otp)
admin_router.post("/auth/forgot-password/reset")(admin_forgot_password_reset)

# Admin Change Password Route (JWT Protected)
admin_router.put("/auth/change-password")(admin_change_password)

# Admin Profile Routes (JWT Protected)
admin_router.get("/profile")(get_admin_profile)
admin_router.put("/profile")(update_admin_profile)


# Dashboard Routes
admin_router.get("/dashboard/overview", response_model=OverviewResponse)(get_overview)
admin_router.get("/dashboard/users", response_model=list[UserResponsedash])(get_all_users)

# User Management Routes
admin_router.post("/register-user", response_model=UserRegisterSchema)(register_user)
admin_router.get("/users", response_model=dict)(get_users_paginated)
admin_router.get("/user/{user_id}", response_model=UserResponse)(get_user_by_id)
admin_router.put("/update-user/{user_id}", response_model=UserResponse)(update_user)
admin_router.delete("/user/{user_id}", response_model=dict)(delete_user)

# User Subscriptions Management Routes
admin_router.get("/user-subscriptions", response_model=dict)(get_user_subscriptions_paginated)
admin_router.get("/user-subscription/{subscription_id}", response_model=UserSubscriptionResponse)(get_user_subscription_by_id)
admin_router.put("/update-user-subscription/{subscription_id}", response_model=UserSubscriptionResponse)(update_user_subscription)


# Workout Management Routes
admin_router.post("/workouts", response_model=WorkoutResponse)(create_workout)
admin_router.get("/workouts", response_model=dict)(get_workouts_paginated)
admin_router.get("/workout/{workout_id}", response_model=WorkoutResponse)(get_workout_by_id)
admin_router.put("/update-workout/{workout_id}", response_model=WorkoutResponse)(update_workout)
admin_router.delete("/workout/{workout_id}")(delete_workout)


# Meal Management Routes
admin_router.post("/meals", response_model=MealResponse)(create_meal)
admin_router.get("/meals", response_model=dict)(get_meals_paginated)
admin_router.get("/meal/{meal_id}", response_model=MealResponse)(get_meal_by_id)
admin_router.put("/update-meal/{meal_id}", response_model=MealResponse)(update_meal)
admin_router.delete("/meal/{meal_id}")(delete_meal)


# BMI Classification Management Routes
admin_router.post("/bmi-classifications", response_model=BMIClassificationResponse)(create_bmi_classification)
admin_router.get("/bmi-classifications", response_model=dict)(get_bmi_classifications_paginated)
admin_router.get("/bmi-classification/{bmi_id}", response_model=BMIClassificationResponse)(get_bmi_classification_by_id)
admin_router.put("/update-bmi-classification/{bmi_id}", response_model=BMIClassificationResponse)(update_bmi_classification)
admin_router.delete("/bmi-classification/{bmi_id}")(delete_bmi_classification)


#Subscription Plans Management routes
admin_router.post("/plans", response_model=Plan)(create_plan)
admin_router.get("/plans", response_model=list[Plan])(get_plans)
admin_router.get("/plan/{plan_id}", response_model=Plan)(get_plan_by_id)
admin_router.put("/update-plan/{plan_id}", response_model=Plan)(update_plan)
admin_router.delete("/delete-plan/{plan_id}")(delete_plan)

# User Activity Logs Routes
admin_router.get("/recent-activities")(get_recent_activities)

# Notification Management Routes
admin_router.get("/notifications")(get_notifications)
admin_router.get("/notifications/stats")(get_notification_stats)
admin_router.get("/notifications/activity-types")(get_activity_types)
admin_router.put("/notifications/{notification_id}/mark-read")(mark_notification_as_read)
admin_router.put("/notifications/mark-all-read")(mark_all_notifications_as_read)
admin_router.get("/notifications/unread-count")(get_unread_notifications_count)

