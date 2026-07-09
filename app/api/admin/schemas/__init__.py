"""
Admin Schemas Package
This package contains all the schemas used by the admin API
"""

from .auth import (
    AdminBase, AdminRegister, AdminLogin, AdminResponse,
    AdminForgotPasswordEmailSchema, AdminForgotPasswordVerifySchema,
    AdminForgotPasswordResetSchema, AdminChangePasswordSchema,
    AdminProfileUpdateSchema, TokenResponse, AdminRefreshTokenRequest,
    AdminRefreshTokenResponse, AdminLogoutRequest
)

from .user import (
    UserRegisterSchema, UserRegisterResponse, UserBase, UserResponse,
    UserUpdate, UserBlockResponse, UserResponsedash, UserAnalyticsResponse
)

from .workout import (
    WorkoutBase, WorkoutCreate, WorkoutUpdate, WorkoutResponse
)

from .meal import (
    MealBase, MealCreate, MealUpdate, MealResponse
)

from .bmi import (
    BMIClassificationBase, BMIClassificationCreate, BMIClassificationResponse,
    BMIClassificationUpdate
)

from .subscription import (
    PlanBase, PlanCreate, PlanUpdate, Plan, UserSubscriptionResponse,
    UserSubscriptionUpdate
)

from .common import (
    PaginationInfo, PaginatedResponse, ErrorResponse, SuccessResponse
)

from .dashboard import OverviewResponse

from .quotes import (
    QuoteBase, QuoteCreate, QuoteUpdate, QuoteResponse
)

from .explore_activity import (
    ExploreActivityBase, ExploreActivityCreate, ExploreActivityUpdate, ExploreActivityResponse
)

from .feedback import (
    FeedbackResponse, FeedbackStatusUpdate, FeedbackAnalyticsSummary
)

__all__ = [
    # Auth schemas
    "AdminBase", "AdminRegister", "AdminLogin", "AdminResponse",
    "AdminForgotPasswordEmailSchema", "AdminForgotPasswordVerifySchema",
    "AdminForgotPasswordResetSchema", "AdminChangePasswordSchema",
    "AdminProfileUpdateSchema", "TokenResponse", "AdminRefreshTokenRequest",
    "AdminRefreshTokenResponse", "AdminLogoutRequest",
    
    # User schemas
    "UserRegisterSchema", "UserRegisterResponse", "UserBase", "UserResponse",
    "UserUpdate", "UserBlockResponse", "UserResponsedash", "UserAnalyticsResponse",
    
    # Workout schemas
    "WorkoutBase", "WorkoutCreate", "WorkoutUpdate", "WorkoutResponse",
    
    # Meal schemas
    "MealBase", "MealCreate", "MealUpdate", "MealResponse",
    
    # BMI schemas
    "BMIClassificationBase", "BMIClassificationCreate", "BMIClassificationResponse",
    "BMIClassificationUpdate",
    
    # Subscription schemas
    "PlanBase", "PlanCreate", "PlanUpdate", "Plan", "UserSubscriptionResponse",
    "UserSubscriptionUpdate",
    
    # Common schemas
    "PaginationInfo", "PaginatedResponse", "ErrorResponse", "SuccessResponse",
    
    # Dashboard schemas
    "OverviewResponse",
    
    # Quote schemas
    "QuoteBase", "QuoteCreate", "QuoteUpdate", "QuoteResponse",
    
    # Explore Activity schemas
    "ExploreActivityBase", "ExploreActivityCreate", "ExploreActivityUpdate", "ExploreActivityResponse",
    
    # Feedback schemas
    "FeedbackResponse", "FeedbackStatusUpdate", "FeedbackAnalyticsSummary"
]
