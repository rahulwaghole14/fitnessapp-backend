import sys
import os
from unittest.mock import MagicMock

# Add workspace directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.meal_service import MealService
from app.models.meal import Meal

class MockMeal:
    def __init__(self, id: int, calories: int, meal_type: str):
        self.id = id
        self.calories = calories
        self.meal_type = meal_type

def test_calorie_target_mapping():
    print("Running test_calorie_target_mapping...")
    # Underweight mapping
    assert MealService.get_daily_calorie_target(1, "Severe Thinness") == 2800
    assert MealService.get_daily_calorie_target(2, "Moderate Thinness") == 2800
    assert MealService.get_daily_calorie_target(3, "Mild Thinness") == 2800
    # Normal mapping
    assert MealService.get_daily_calorie_target(4, "Normal") == 2200
    # Overweight mapping
    assert MealService.get_daily_calorie_target(5, "Overweight") == 1800
    # Obese mapping
    assert MealService.get_daily_calorie_target(6, "Obese Class I") == 1500
    assert MealService.get_daily_calorie_target(7, "Obese Class II") == 1500
    assert MealService.get_daily_calorie_target(8, "Obese Class III") == 1500
    print("test_calorie_target_mapping passed!")

def test_combination_selection():
    print("Running test_combination_selection...")
    
    # Setup test case (similar to prompt example)
    # Target: 660 kcal
    # Available: A=150, B=200, C=300, D=120
    # Closest combination: C(300) + B(200) + A(150) = 650 kcal (deviation = 10)
    # Greedy ascending combination: D(120) + A(150) + B(200) + C(300) = 770 kcal (deviation = 110)
    meals = [
        MockMeal(1, 150, "breakfast"),
        MockMeal(2, 200, "breakfast"),
        MockMeal(3, 300, "breakfast"),
        MockMeal(4, 120, "breakfast"),
    ]
    
    closest = MealService.find_closest_combination(meals, 660)
    total_cal = sum(m.calories for m in closest)
    
    print(f"Target: 660, Selected calories: {total_cal}, Selected meal IDs: {[m.id for m in closest]}")
    assert total_cal == 650, f"Expected 650, got {total_cal}"
    
    # Test case 2: Exact match available
    # Target: 880 kcal
    # Available: A=400, B=480, C=300, D=200
    # Closest combination: A(400) + B(480) = 880 (exact match)
    meals2 = [
        MockMeal(1, 400, "lunch"),
        MockMeal(2, 480, "lunch"),
        MockMeal(3, 300, "lunch"),
        MockMeal(4, 200, "lunch"),
    ]
    closest2 = MealService.find_closest_combination(meals2, 880)
    total_cal2 = sum(m.calories for m in closest2)
    print(f"Target: 880, Selected calories: {total_cal2}, Selected meal IDs: {[m.id for m in closest2]}")
    assert total_cal2 == 880
    
    # Test case 3: Empty list
    closest3 = MealService.find_closest_combination([], 500)
    assert closest3 == []
    
    # Test case 4: Single extremely large meal
    # Target: 500
    # Available: A=1000
    # Closest sum: A=1000 (deviation = 500), empty subset (deviation = 500)
    # Tie-breaker should pick empty subset because of fewer elements.
    meals4 = [MockMeal(1, 1000, "dinner")]
    closest4 = MealService.find_closest_combination(meals4, 500)
    total_cal4 = sum(m.calories for m in closest4)
    print(f"Target: 500, Selected calories: {total_cal4}, Selected meal IDs: {[m.id for m in closest4]}")
    assert len(closest4) == 0 or total_cal4 == 1000
    
    print("test_combination_selection passed!")

def test_database_plan_generation():
    print("Running test_database_plan_generation...")
    from app.core.database import SessionLocal
    from app.models.user import User
    
    db = SessionLocal()
    try:
        # Check if user "jagga daku" exists
        user = db.query(User).filter(User.username == 'jagga daku').first()
        if not user:
            # Fallback to any user with a BMI
            user = db.query(User).filter(User.bmi.isnot(None)).first()
            
        if not user:
            print("No user found in DB, skipping database plan generation test.")
            return
            
        print(f"Generating meal plan for user: {user.username} (BMI: {user.bmi})")
        plan = MealService.generate_meal_plan(db, user)
        print("Generated Plan Details:")
        print(f"  BMI Category: {plan.bmi_category}")
        print(f"  Daily Target Calories: {plan.daily_target_calories}")
        print(f"  Breakfast Target: {plan.breakfast.target_calories}, Actual: {plan.breakfast.actual_calories}, Meals: {len(plan.breakfast.meals)}")
        print(f"  Lunch Target: {plan.lunch.target_calories}, Actual: {plan.lunch.actual_calories}, Meals: {len(plan.lunch.meals)}")
        print(f"  Dinner Target: {plan.dinner.target_calories}, Actual: {plan.dinner.actual_calories}, Meals: {len(plan.dinner.meals)}")
        print(f"  Total Actual Calories: {plan.total_actual_calories}")
        
        assert plan.daily_target_calories in (1500, 1800, 2200, 2800)
        assert plan.breakfast.actual_calories >= 0
        assert plan.lunch.actual_calories >= 0
        assert plan.dinner.actual_calories >= 0
        assert plan.total_actual_calories == plan.breakfast.actual_calories + plan.lunch.actual_calories + plan.dinner.actual_calories
        
        print("test_database_plan_generation passed!")
    except Exception as e:
        print(f"Database test failed: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    test_calorie_target_mapping()
    test_combination_selection()
    test_database_plan_generation()
    print("All tests passed successfully!")
