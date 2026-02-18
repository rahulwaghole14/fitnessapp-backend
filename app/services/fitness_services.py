from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from typing import Optional, Tuple
import calendar


class FitnessActivityService:

    def __init__(self, db: Session):
        self.db = db

    def get_previous_month_info(self, current_date: date) -> Optional[Tuple[int, int]]:

        if current_date.month == 1:
            return None  # No previous month for January

        previous_month = current_date.month - 1
        previous_year = current_date.year

        return previous_year, previous_month

    def check_daily_record_exists(self, user_id: int, activity_date: date) -> bool:
        result = self.db.execute(text("""
                                      SELECT COUNT(*)
                                      FROM daily_activities
                                      WHERE user_id = :user_id AND date = :activity_date
                                      """), {"user_id": user_id, "activity_date": activity_date})

        return result.scalar() > 0

    def upsert_daily_activity(self, user_id: int, activity_date: date, steps: int,
                              distance_km: float, calories: float, active_minutes: float) -> int:

        if self.check_daily_record_exists(user_id, activity_date):
            # Update existing record
            result = self.db.execute(text("""
                                          UPDATE daily_activities
                                          SET steps          = :steps,
                                              distance_km    = :distance_km,
                                              calories       = :calories,
                                              active_minutes = :active_minutes
                                          WHERE user_id = :user_id
                                            AND date = :activity_date
                                              RETURNING id
                                          """), {
                                         "user_id": user_id,
                                         "activity_date": activity_date,
                                         "steps": steps,
                                         "distance_km": distance_km,
                                         "calories": calories,
                                         "active_minutes": active_minutes
                                     })
        else:
            # Insert new record
            result = self.db.execute(text("""
                                          INSERT INTO daily_activities
                                          (user_id, date, steps, distance_km, calories, active_minutes, created_at)
                                          VALUES (:user_id, :activity_date, :steps, :distance_km, :calories,
                                                  :active_minutes, NOW()) RETURNING id
                                          """), {
                                         "user_id": user_id,
                                         "activity_date": activity_date,
                                         "steps": steps,
                                         "distance_km": distance_km,
                                         "calories": calories,
                                         "active_minutes": active_minutes
                                     })

        self.db.commit()
        return result.scalar()

    def get_monthly_daily_records(self, user_id: int, year: int, month: int) -> list:
        result = self.db.execute(text("""
                                      SELECT steps, distance_km, calories, active_minutes
                                      FROM daily_activities
                                      WHERE user_id = :user_id
                                        AND EXTRACT(YEAR FROM date) = :year
                                        AND EXTRACT(MONTH FROM date) = :month
                                      ORDER BY date
                                      """), {"user_id": user_id, "year": year, "month": month})

        return result.fetchall()

    def check_monthly_summary_exists(self, user_id: int, year: int, month: int) -> bool:
        result = self.db.execute(text("""
                                      SELECT COUNT(*)
                                      FROM user_monthly_activity
                                      WHERE user_id = :user_id AND year = :year AND month = :month
                                      """), {"user_id": user_id, "year": year, "month": month})

        return result.scalar() > 0

    def create_monthly_summary(self, user_id: int, year: int, month: int,
                               total_steps: int, total_distance: float,
                               total_calories: float, total_active_minutes: float) -> int:

        result = self.db.execute(text("""
                                      INSERT INTO user_monthly_activity
                                      (user_id, year, month, total_steps, total_distance_km,
                                       total_calories, total_active_minutes, created_at)
                                      VALUES (:user_id, :year, :month, :total_steps, :total_distance_km,
                                              :total_calories, :total_active_minutes, NOW()) RETURNING id
                                      """), {
                                     "user_id": user_id,
                                     "year": year,
                                     "month": month,
                                     "total_steps": total_steps,
                                     "total_distance_km": total_distance,
                                     "total_calories": total_calories,
                                     "total_active_minutes": total_active_minutes
                                 })

        self.db.commit()
        return result.scalar()

    def delete_daily_records_for_month(self, user_id: int, year: int, month: int) -> int:
        result = self.db.execute(text("""
                                      DELETE
                                      FROM daily_activities
                                      WHERE user_id = :user_id
                                        AND EXTRACT(YEAR FROM date) = :year
                                        AND EXTRACT(MONTH FROM date) = :month
                                      """), {"user_id": user_id, "year": year, "month": month})

        self.db.commit()
        return result.rowcount

    def enforce_12_month_retention(self, user_id: int) -> int:

        # Get count of monthly records
        result = self.db.execute(text("""
                                      SELECT COUNT(*)
                                      FROM user_monthly_activity
                                      WHERE user_id = :user_id
                                      """), {"user_id": user_id})

        count = result.scalar()
        if count <= 12:
            return 0

        # Delete-oldest records (keep only 12 most recent)
        records_to_delete = count - 12
        result = self.db.execute(text("""
                                      DELETE
                                      FROM user_monthly_activity
                                      WHERE id IN (SELECT id
                                                   FROM user_monthly_activity
                                                   WHERE user_id = :user_id
                                                   ORDER BY year ASC, month ASC 
                LIMIT :records_to_delete
            )
                                      """), {"user_id": user_id, "records_to_delete": records_to_delete})

        self.db.commit()
        return result.rowcount

    #YEARLY AGGREGATION METHOD

    def check_yearly_summary_exists(self, user_id: int, year: int) -> bool:
        result = self.db.execute(text("""
                                      SELECT COUNT(*)
                                      FROM user_yearly_activity
                                      WHERE user_id = :user_id AND year = :year
                                      """), {"user_id": user_id, "year": year})

        return result.scalar() > 0

    def create_yearly_summary(self, user_id: int, year: int,
                              total_steps: int, total_distance: float,
                              total_calories: float, total_active_minutes: float) -> int:

        result = self.db.execute(text("""
                                      INSERT INTO user_yearly_activity
                                      (user_id, year, total_steps, total_distance_km,
                                       total_calories, total_active_minutes, created_at)
                                      VALUES (:user_id, :year, :total_steps, :total_distance_km,
                                              :total_calories, :total_active_minutes, NOW()) RETURNING id
                                      """), {
                                     "user_id": user_id,
                                     "year": year,
                                     "total_steps": total_steps,
                                     "total_distance_km": total_distance,
                                     "total_calories": total_calories,
                                     "total_active_minutes": total_active_minutes
                                 })

        self.db.commit()
        return result.scalar()

    def get_yearly_monthly_records(self, user_id: int, year: int) -> list:
        result = self.db.execute(text("""
                                      SELECT total_steps, total_distance_km, total_calories, total_active_minutes
                                      FROM user_monthly_activity
                                      WHERE user_id = :user_id AND year = :year
                                      ORDER BY month
                                      """), {"user_id": user_id, "year": year})

        return result.fetchall()

    def delete_monthly_records_for_year(self, user_id: int, year: int) -> int:
        """Delete all monthly records for a specific year"""
        result = self.db.execute(text("""
                                      DELETE
                                      FROM user_monthly_activity
                                      WHERE user_id = :user_id AND year = :year
                                      """), {"user_id": user_id, "year": year})

        self.db.commit()
        return result.rowcount

    def should_trigger_yearly_aggregation(self, user_id: int, activity_date: date) -> bool:

        # Get the most recent monthly record for this user
        result = self.db.execute(text("""
                                      SELECT year, month
                                      FROM user_monthly_activity
                                      WHERE user_id = :user_id
                                      ORDER BY year DESC, month DESC
                                          LIMIT 1
                                      """), {"user_id": user_id})

        most_recent_monthly = result.fetchone()

        if not most_recent_monthly:
            return False

        most_recent_year = most_recent_monthly[0]
        most_recent_month = most_recent_monthly[1]

        # Check if most recent was December (12) and current is January (1)
        if most_recent_month == 12 and activity_date.month == 1:
            # Check if yearly summary exists for the completed year
            if not self.check_yearly_summary_exists(user_id, most_recent_year):
                # Store year to be aggregated for later use
                self._year_to_aggregate = most_recent_year
                return True

        return False

    def aggregate_and_store_yearly_summary(self, user_id: int, year: int) -> Optional[dict]:

        # Get all monthly records for the year
        monthly_records = self.get_yearly_monthly_records(user_id, year)

        # Always create yearly summary (even if no monthly records)
        if not monthly_records:
            # Create zero summary for years with no monthly data
            yearly_id = self.create_yearly_summary(
                user_id, year, 0, 0.0, 0.0, 0.0
            )

            return {
                'yearly_id': yearly_id,
                'total_steps': 0,
                'total_distance_km': 0.0,
                'total_calories': 0.0,
                'total_active_minutes': 0.0,
                'monthly_records_deleted': 0
            }

        # Aggregate the data
        total_steps = sum(record[0] for record in monthly_records)
        total_distance = sum(record[1] for record in monthly_records)
        total_calories = sum(record[2] for record in monthly_records)
        total_active_minutes = sum(record[3] for record in monthly_records)

        # Create yearly summary
        yearly_id = self.create_yearly_summary(
            user_id, year, total_steps,
            total_distance, total_calories, total_active_minutes
        )

        # Delete monthly records for that year
        deleted_count = self.delete_monthly_records_for_year(user_id, year)

        return {
            'yearly_id': yearly_id,
            'total_steps': total_steps,
            'total_distance_km': total_distance,
            'total_calories': total_calories,
            'total_active_minutes': total_active_minutes,
            'monthly_records_deleted': deleted_count
        }

    def aggregate_and_store_monthly_summary(self, user_id: int, year: int, month: int) -> Optional[dict]:

        # Get all daily records for the month
        daily_records = self.get_monthly_daily_records(user_id, year, month)

        # Always create monthly summary (even if no daily records)
        if not daily_records:
            # Create zero summary for months with no daily data
            monthly_id = self.create_monthly_summary(
                user_id, year, month, 0, 0.0, 0.0, 0.0
            )

            return {
                'monthly_id': monthly_id,
                'total_steps': 0,
                'total_distance_km': 0.0,
                'total_calories': 0.0,
                'total_active_minutes': 0.0,
                'daily_records_deleted': 0,
                'old_monthly_records_deleted': 0
            }

        # Aggregate the data
        total_steps = sum(record[0] for record in daily_records)
        total_distance = sum(record[1] for record in daily_records)
        total_calories = sum(record[2] for record in daily_records)
        total_active_minutes = sum(record[3] for record in daily_records)

        # Create monthly summary
        monthly_id = self.create_monthly_summary(
            user_id, year, month, total_steps,
            total_distance, total_calories, total_active_minutes
        )

        # Delete daily records for that month
        deleted_count = self.delete_daily_records_for_month(user_id, year, month)

        # Enforce 12-month retention
        old_records_deleted = self.enforce_12_month_retention(user_id)

        return {
            'monthly_id': monthly_id,
            'total_steps': total_steps,
            'total_distance_km': total_distance,
            'total_calories': total_calories,
            'total_active_minutes': total_active_minutes,
            'daily_records_deleted': deleted_count,
            'old_monthly_records_deleted': old_records_deleted
        }

    def should_trigger_monthly_summary(self, user_id: int, activity_date: date) -> bool:

        # Get all months that have daily records for this user
        result = self.db.execute(text("""
                                      SELECT DISTINCT EXTRACT(YEAR FROM date) as year, 
                   EXTRACT(MONTH FROM date) as month
                                      FROM daily_activities
                                      WHERE user_id = :user_id
                                      ORDER BY year DESC, month DESC
                                      """), {"user_id": user_id})

        months_with_data = result.fetchall()

        if not months_with_data:
            return False

        # Get current month from the activity being inserted
        current_year = activity_date.year
        current_month = activity_date.month

        # Find the most recent month with data (excluding current month)
        most_recent_year = None
        most_recent_month = None

        for year, month in months_with_data:
            year = int(year)
            month = int(month)

            # Skip current month
            if year == current_year and month == current_month:
                continue

            # Find the most recent month
            if most_recent_year is None or (year > most_recent_year) or \
                    (year == most_recent_year and month > most_recent_month):
                most_recent_year = year
                most_recent_month = month

        # If no previous month data, no aggregation needed
        if most_recent_year is None:
            return False

        # Check if summary exists for the most recent month
        if self.check_monthly_summary_exists(user_id, most_recent_year, most_recent_month):
            return False

        # Store the month to be aggregated for later use
        self._month_to_aggregate_year = most_recent_year
        self._month_to_aggregate_month = most_recent_month

        return True

    def get_user_monthly_activities(self, user_id: int) -> list:

        result = self.db.execute(text("""
                                      SELECT id, year, month, total_steps, total_distance_km, total_calories, total_active_minutes, created_at
                                      FROM user_monthly_activity
                                      WHERE user_id = :user_id
                                      ORDER BY year DESC, month DESC
                                      """), {"user_id": user_id})

        return result.fetchall()

    def check_yearly_monthly_records_exist(self, user_id: int, year: int) -> bool:
        result = self.db.execute(text("""
                                      SELECT COUNT(*)
                                      FROM user_monthly_activity
                                      WHERE user_id = :user_id AND year = :year
                                      """), {"user_id": user_id, "year": year})

        return result.scalar() > 0

    def check_all_q1_months_exist(self, user_id: int, year: int) -> bool:
        result = self.db.execute(text("""
                                      SELECT COUNT(DISTINCT month) 
                                      FROM user_monthly_activity 
                                      WHERE user_id = :user_id AND year = :year AND month IN (1, 2, 3)
                                      """), {"user_id": user_id, "year": year})
        
        distinct_months = result.scalar()
        return distinct_months == 3  # All 3 Q1 months must exist

    def check_any_q1_month_exists(self, user_id: int, year: int) -> bool:
        result = self.db.execute(text("""
                                      SELECT COUNT(*) 
                                      FROM user_monthly_activity 
                                      WHERE user_id = :user_id AND year = :year AND month IN (1, 2, 3)
                                      """), {"user_id": user_id, "year": year})
        
        count = result.scalar()
        return count > 0  # Any Q1 month exists

    def check_partial_q1_months_count(self, user_id: int, year: int) -> int:
        result = self.db.execute(text("""
                                      SELECT COUNT(DISTINCT month) 
                                      FROM user_monthly_activity 
                                      WHERE user_id = :user_id AND year = :year AND month IN (1, 2, 3)
                                      """), {"user_id": user_id, "year": year})
        
        distinct_months = result.scalar()
        return distinct_months  # Returns 0, 1, 2, or 3
