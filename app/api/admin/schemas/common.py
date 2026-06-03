"""
Common schemas used across admin API
"""
from pydantic import BaseModel
from typing import List, Generic, TypeVar, Optional

# Generic Type for Paginated Response
T = TypeVar('T')

# Pagination Schema
class PaginationInfo(BaseModel):
    page: int
    limit: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    pagination: PaginationInfo

# Error Response Schema
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None

# Success Response Schema
class SuccessResponse(BaseModel):
    message: str
    data: Optional[dict] = None
