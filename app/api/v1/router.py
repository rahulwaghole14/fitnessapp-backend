from fastapi import APIRouter

from .auth import (
    register, login,
    forgot_password_send_otp, resend_otp, forgot_password_verify_otp, forgot_password_reset_password,
    update_profile, get_profile,upload_profile_image, get_user_profile, change_password)

from .auth_tokens import refresh_token, logout, logout_all

from .activities import (store_daily_activity, get_weekly_analytics,
                         get_user_daily_activities, get_user_monthly_activities,get_user_yearly_activities)
from .meals import get_meals_by_user_bmi
from .workouts import get_workouts_for_user
from .subscription import (get_all_plans, get_plan_id, create_subscription_order, handle_razorpay_webhook,
                           get_payment_history ,get_user_subscription)
from .quotes import get_random_quote, get_quotes_list
from .sleep import (
    create_session, update_session, delete_session, get_session,
    get_history, get_daily, get_monthly, get_yearly, get_analytics
)
from .notifications import (
    get_user_notifications, get_user_unread_count,
    mark_user_notification_as_read, mark_all_user_notifications_as_read,
    delete_user_notification
)

from app.schemas.notification import (
    NotificationListResponse, UnreadCountResponse,
    NotificationMarkReadResponse, NotificationSuccessResponse
)

from app.schemas.subscription import Plan
from app.schemas.payment import OrderResponse, PaymentHistory
from app.schemas.quote import QuoteResponse, QuoteListResponse
from app.schemas.sleep import (
    SleepSessionResponse, SleepHistoryResponse, UserDailySleepResponse,
    UserMonthlySleepResponse, UserYearlySleepResponse, SleepAnalyticsResponse
)

router = APIRouter()

# Notification Endpoints
router.get("/notifications", response_model=NotificationListResponse)(get_user_notifications)
router.get("/notifications/unread-count", response_model=UnreadCountResponse)(get_user_unread_count)
router.put("/notifications/{id}/read", response_model=NotificationMarkReadResponse)(mark_user_notification_as_read)
router.put("/notifications/mark-all-read", response_model=NotificationSuccessResponse)(mark_all_user_notifications_as_read)
router.delete("/notifications/{id}", response_model=NotificationSuccessResponse)(delete_user_notification)

#Auth endpoints
router.post("/register")(register),
router.post("/forgot-password/send-otp")(forgot_password_send_otp),
router.post("/resend-otp")(resend_otp)
router.post("/forgot-password/verify-otp")(forgot_password_verify_otp),
router.post("/forgot-password/reset-password")(forgot_password_reset_password),
router.post("/login")(login),
router.put("/setup-profile")(update_profile),
router.get("/profile")(get_profile),
# Profile image endpoints
router.put("/users/profile-image")(upload_profile_image)
router.get("/users/profile")(get_user_profile)

# Change password endpoint
router.put("/change-password")(change_password)

# JWT Token endpoints
router.post("/auth/refresh")(refresh_token),
router.post("/auth/logout")(logout),
router.post("/auth/logout-all")(logout_all)


#Activity Endpoints
router.post("/activity/daily")(store_daily_activity)  # New fitness endpoint with auto-summarization
router.get("/activity/weekly")(get_weekly_analytics)  # get the user data monthly record week wise
router.get("/activity/daily")(get_user_daily_activities)  # get user data of all month daywise
router.get("/activity/monthly")(get_user_monthly_activities)  # New monthly activities endpoint  and get the user data monthly
router.get("/activity/yearly")(get_user_yearly_activities)  # New yearly activities endpoint

# Meal endpoints
router.get("/meals")(get_meals_by_user_bmi)

# Workout endpoints
router.get("/workouts")(get_workouts_for_user)

# Quotes endpoints
router.get("/quotes/random", response_model=QuoteResponse)(get_random_quote)

#Subscription Endpoints
router.get("/subscription-plans", response_model=list[Plan])(get_all_plans)
router.get("/subscription-plans/{plan_id}", response_model=Plan)(get_plan_id)
router.post("/subscriptions/order", response_model=OrderResponse)(create_subscription_order)
router.post("/subscriptions/payment")(handle_razorpay_webhook)
router.get("/subscriptions/payment-history", response_model=list[PaymentHistory])(get_payment_history)
router.get("/subscriptions/user-subscription", response_model=list[dict])(get_user_subscription)

# Sleep Endpoints
router.post("/sleep/session", response_model=SleepSessionResponse, status_code=201)(create_session)
router.put("/sleep/session/{id}", response_model=SleepSessionResponse)(update_session)
router.delete("/sleep/session/{id}")(delete_session)
router.get("/sleep/session/{id}", response_model=SleepSessionResponse)(get_session)
router.get("/sleep/history", response_model=SleepHistoryResponse)(get_history)
router.get("/sleep/daily", response_model=UserDailySleepResponse)(get_daily)
router.get("/sleep/monthly", response_model=UserMonthlySleepResponse)(get_monthly)
router.get("/sleep/yearly", response_model=UserYearlySleepResponse)(get_yearly)
router.get("/sleep/analytics", response_model=SleepAnalyticsResponse)(get_analytics)


