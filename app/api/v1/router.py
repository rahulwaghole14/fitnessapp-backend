from fastapi import APIRouter

from .auth import (
    register, login,
    forgot_password_send_otp, forgot_password_verify_otp, forgot_password_reset_password,
    update_profile, get_profile)

from .activities import store_daily_activity, get_weekly_analytics, get_user_daily_activities, get_user_monthly_activities


router = APIRouter()

#Auth endpoints
router.post("/register")(register),
router.post("/forgot-password/send-otp")(forgot_password_send_otp),
router.post("/forgot-password/verify-otp")(forgot_password_verify_otp),
router.post("/forgot-password/reset-password")(forgot_password_reset_password),
router.post("/login")(login),
router.put("/setup-profile")(update_profile),
router.get("/profile")(get_profile),

#Activity Endpoints
router.post("/activity/daily")(store_daily_activity)  # New fitness endpoint with auto-summarization
router.get("/activity/weekly")(get_weekly_analytics)
router.get("/activity/daily/{user_id}")(get_user_daily_activities)
router.get("/activity/monthly/{user_id}")(get_user_monthly_activities)  # New monthly activities endpoint
# router.get("/activity/yearly/{user_id}")(get_user_yearly_activities)  # New yearly activities endpoint

