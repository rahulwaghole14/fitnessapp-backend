from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class BMIClassificationBase(BaseModel):
    category_name: str
    min_bmi: Optional[float] = None
    max_bmi: Optional[float] = None


class BMIClassificationCreate(BMIClassificationBase):
    pass


class BMIClassificationResponse(BMIClassificationBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
