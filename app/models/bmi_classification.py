
from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.core.database import Base

class BMIClassification(Base):
    __tablename__ = "bmi_classification"

    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String, nullable=False, index=True)
    min_bmi = Column(Float, nullable=True)
    max_bmi = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
