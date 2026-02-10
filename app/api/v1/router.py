from fastapi import APIRouter

from .auth import (
    register, login,
    forgot_password_send_otp, forgot_password_verify_otp, forgot_password_reset_password,
    update_profile, get_profile,upload_profile_image, get_user_profile)

from .auth_tokens import refresh_token, logout, logout_all

from .activities import (store_daily_activity, get_weekly_analytics,
                         get_user_daily_activities, get_user_monthly_activities)
from .meals import get_meals_by_user_bmi, create_bmi_classification, create_meal
from .workouts import create_workout, get_workouts_for_user


router = APIRouter()

#Auth endpoints
router.post("/register")(register),
router.post("/forgot-password/send-otp")(forgot_password_send_otp),
router.post("/forgot-password/verify-otp")(forgot_password_verify_otp),
router.post("/forgot-password/reset-password")(forgot_password_reset_password),
router.post("/login")(login),
router.put("/setup-profile")(update_profile),
router.get("/profile")(get_profile),
# Profile image endpoints
router.put("/users/profile-image")(upload_profile_image)
router.get("/users/profile")(get_user_profile)

# JWT Token endpoints
router.post("/auth/refresh")(refresh_token),
router.post("/auth/logout")(logout),
router.post("/auth/logout-all")(logout_all)


#Activity Endpoints
router.post("/activity/daily")(store_daily_activity)  # New fitness endpoint with auto-summarization
router.get("/activity/weekly")(get_weekly_analytics)  # get the user data monthly record week wise
router.get("/activity/daily")(get_user_daily_activities)  # get user data of all month daywise
router.get("/activity/monthly")(get_user_monthly_activities)  # New monthly activities endpoint  and get the user data monthly
# router.get("/activity/yearly/{user_id}")(get_user_yearly_activities)  # New yearly activities endpoint

# Meal endpoints
router.get("/meals")(get_meals_by_user_bmi)
router.post("/bmi-classification")(create_bmi_classification)
router.post("/meals")(create_meal)

# Workout endpoints
router.post("/workouts")(create_workout)
router.get("/workouts")(get_workouts_for_user)

