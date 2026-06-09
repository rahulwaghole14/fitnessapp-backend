from app.core.database import get_db
from app.models.user import User
from app.models.subscription_plans import Plan
from app.models.refresh_token import RefreshToken
from sqlalchemy.orm import Session

# Create a database session
db = next(get_db())

# Check if user 'jagga daku' exists
user = db.query(User).filter(User.username == 'jagga daku').first()
if user:
    print(f'User found: ID={user.id}, Username={user.username}, Email={user.email}')
else:
    print('User "jagga daku" not found')

# Check available plans
plans = db.query(Plan).filter(Plan.is_active == True).all()
print(f'\nAvailable plans:')
for plan in plans:
    print(f'ID={plan.id}, Name={plan.name}, Price={plan.price}, Duration={plan.duration_days} days')

db.close()
