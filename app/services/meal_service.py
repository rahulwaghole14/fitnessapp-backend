from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from sqlalchemy import or_, and_

from app.models.user import User
from app.models.bmi_classification import BMIClassification
from app.models.meal import Meal
from app.schemas.meal import MealPlanResponse, MealPlanSection, MealResponse


class MealService:
    @staticmethod
    def get_daily_calorie_target(category_id: int, category_name: str) -> int:
        """Map BMI category ID or category name to daily calorie target."""
        # Clean category name for robust string matching
        name_lower = category_name.lower()

        if category_id in (1, 2, 3) or "thinness" in name_lower or "underweight" in name_lower:
            return 2800
        elif category_id == 4 or "normal" in name_lower:
            return 2200
        elif category_id == 5 or "overweight" in name_lower:
            return 1800
        elif category_id in (6, 7, 8) or "obese" in name_lower:
            return 1500
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No daily calorie target mapped for BMI category '{category_name}' (ID: {category_id})."
            )

    @staticmethod
    def find_closest_combination(meals: List[Meal], target: int) -> List[Meal]:
        """
        Finds a subset of meals that minimizes the absolute calorie deviation from target.
        Uses a Dynamic Programming (subset sum style) approach with tie-breaking for fewer meals.
        """
        if not meals:
            return []

        # Sort meals by calories ascending (good practice & optimization rule hint)
        meals = sorted(meals, key=lambda m: m.calories)

        # Optimization / Pruning heuristic: if we have more than 20 candidate meals,
        # we pick the 15 smallest meals plus the 5 meals closest to the target.
        # This keeps the DP state space small while retaining good combination candidates.
        if len(meals) > 20:
            candidates = meals[:15]
            closest_to_target = sorted(meals, key=lambda m: abs(m.calories - target))
            for m in closest_to_target:
                if len(candidates) >= 20:
                    break
                if m not in candidates:
                    candidates.append(m)
            meals = candidates

        # Find the max calorie value in the filtered list
        max_calories = max(m.calories for m in meals)
        
        # Upper bound of calorie sum we care to track:
        # Any combination with sum > 2 * target has deviation > target, which is worse than
        # empty set (sum 0, deviation = target) or a single close meal.
        limit = max(2 * target, max_calories)

        # dp[s] stores the subset of meals that sums to s
        dp = {0: []}

        for meal in meals:
            new_dp = {}
            for s, subset in dp.items():
                new_sum = s + meal.calories
                if new_sum <= limit:
                    # If this sum hasn't been reached, or we found a subset with fewer meals (tie-breaker)
                    if new_sum not in dp or new_sum not in new_dp:
                        new_dp[new_sum] = subset + [meal]
                    else:
                        existing_subset = dp.get(new_sum) or new_dp[new_sum]
                        if len(subset) + 1 < len(existing_subset):
                            new_dp[new_sum] = subset + [meal]
            dp.update(new_dp)

        # Find the sum that minimizes the absolute deviation from the target
        best_sum = None
        best_deviation = float('inf')

        for s in dp.keys():
            dev = abs(s - target)
            if dev < best_deviation:
                best_deviation = dev
                best_sum = s
            elif dev == best_deviation:
                # Tie-breaker: prefer fewer meals
                if len(dp[s]) < len(dp[best_sum]):
                    best_sum = s

        return dp[best_sum] if best_sum is not None else []

    @staticmethod
    def generate_meal_plan(db: Session, current_user: User) -> MealPlanResponse:
        """
        Validates user BMI, resolves BMI category, fetches all category meals,
        distributes target calories, and runs the meal selection engine.
        """
        # 1. Validate User BMI
        if current_user.bmi is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User BMI is missing. Please set up your profile weight and height to calculate BMI."
            )

        bmi_value = current_user.bmi

        # 2. Resolve BMI Category
        bmi_category = db.query(BMIClassification).filter(
            or_(
                and_(BMIClassification.min_bmi <= bmi_value, BMIClassification.max_bmi >= bmi_value),
                and_(BMIClassification.min_bmi.is_(None), BMIClassification.max_bmi >= bmi_value),
                and_(BMIClassification.min_bmi <= bmi_value, BMIClassification.max_bmi.is_(None))
            )
        ).first()

        if not bmi_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No BMI category found in database matching BMI {bmi_value}."
            )

        # 3. Get Calorie Target & Distribute
        daily_target = MealService.get_daily_calorie_target(bmi_category.id, bmi_category.category_name)
        
        target_breakfast = int(round(daily_target * 0.30))
        target_lunch = int(round(daily_target * 0.40))
        target_dinner = int(round(daily_target * 0.30))

        # 4. Fetch All Meals for this BMI category
        all_meals = db.query(Meal).filter(Meal.bmi_category_id == bmi_category.id).all()

        if not all_meals:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No meals configured for BMI category '{bmi_category.category_name}'."
            )

        # Segment by meal type
        breakfast_meals = [m for m in all_meals if m.meal_type.lower() == 'breakfast']
        lunch_meals = [m for m in all_meals if m.meal_type.lower() == 'lunch']
        dinner_meals = [m for m in all_meals if m.meal_type.lower() == 'dinner']

        # 5. Handle empty collections
        empty_sections = []
        if not breakfast_meals:
            empty_sections.append("breakfast")
        if not lunch_meals:
            empty_sections.append("lunch")
        if not dinner_meals:
            empty_sections.append("dinner")

        if empty_sections:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No meals found for category '{bmi_category.category_name}' under the following types: {', '.join(empty_sections)}."
            )

        # 6. Select Meals
        selected_breakfast = MealService.find_closest_combination(breakfast_meals, target_breakfast)
        selected_lunch = MealService.find_closest_combination(lunch_meals, target_lunch)
        selected_dinner = MealService.find_closest_combination(dinner_meals, target_dinner)

        # Calculate actual calories
        actual_breakfast_cal = sum(m.calories for m in selected_breakfast)
        actual_lunch_cal = sum(m.calories for m in selected_lunch)
        actual_dinner_cal = sum(m.calories for m in selected_dinner)
        total_actual_cal = actual_breakfast_cal + actual_lunch_cal + actual_dinner_cal

        # 7. Construct Response
        return MealPlanResponse(
            bmi_category=bmi_category.category_name,
            daily_target_calories=daily_target,
            breakfast=MealPlanSection(
                target_calories=target_breakfast,
                actual_calories=actual_breakfast_cal,
                meals=[MealResponse.model_validate(m) for m in selected_breakfast]
            ),
            lunch=MealPlanSection(
                target_calories=target_lunch,
                actual_calories=actual_lunch_cal,
                meals=[MealResponse.model_validate(m) for m in selected_lunch]
            ),
            dinner=MealPlanSection(
                target_calories=target_dinner,
                actual_calories=actual_dinner_cal,
                meals=[MealResponse.model_validate(m) for m in selected_dinner]
            ),
            total_actual_calories=total_actual_cal
        )
