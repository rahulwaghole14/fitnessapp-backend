from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class QuoteBase(BaseModel):
    text: str
    author: Optional[str] = None
    category: Optional[str] = None

class QuoteResponse(QuoteBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class QuoteListResponse(BaseModel):
    quotes: list[QuoteResponse]
    total: int
    page: int
    limit: int
