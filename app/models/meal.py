from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Meal(Base):
    __tablename__ = "meals"

    id = Column(Integer, primary_key=True, index=True)
    bmi_category_id = Column(Integer, ForeignKey("bmi_classification.id"), nullable=False, index=True)
    meal_type = Column(String, nullable=False, index=True)  # breakfast, lunch, dinner
    food_item = Column(String, nullable=False)
    calories = Column(Integer, nullable=False)
    meal_image = Column(String, nullable=True)  # URL to uploaded image
    description = Column(Text, nullable=True)  # Meal description
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship with BMIClassification
    bmi_category = relationship("BMIClassification", backref="meals")
