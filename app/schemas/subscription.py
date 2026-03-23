from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List, Union, Any
from datetime import datetime
import json

class PlanBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    duration_days: int  # Changed from duration_months
    features: Optional[List[str]] = None  # Changed from str to List[str]
    is_active: bool = True

class Plan(PlanBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_validator('features', mode='before')
    @classmethod
    def parse_features(cls, v):
        """Parse features from database JSON string to list"""
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                elif isinstance(parsed, dict):
                    # Convert dict values to list of strings
                    return [f"{k}:{v}" for k, v_item in parsed.items()]
                return [str(parsed)]
            except (json.JSONDecodeError, TypeError):
                return [str(v)]
        return [str(v)]

