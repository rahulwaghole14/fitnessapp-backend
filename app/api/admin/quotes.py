from fastapi import HTTPException, Query, status, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.quotes import Quote
from app.api.admin.schemas import QuoteCreate, QuoteResponse, QuoteUpdate, SuccessResponse
from app.api.admin.dependencies import get_current_admin
from app.models.admin import Admin


# Admin endpoints (Protected)
def create_new_quote(
    quote_data: QuoteCreate, 
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Create a new motivational quote (Admin only)
    """
    # Quote creation
    db_quote = Quote(
        text=quote_data.text,
        author=quote_data.author,
        category=quote_data.category
    )
    db.add(db_quote)
    db.commit()
    db.refresh(db_quote)
    
    return db_quote

def list_all_quotes_for_admin(
    skip: int = Query(0, ge=0, description="Number of quotes to skip"), 
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of quotes to return"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Get all active quotes with pagination (Admin only)
    """
    # Database query with pagination
    quotes = db.query(Quote).offset(skip).limit(limit).all()
    return quotes

def modify_existing_quote(
    quote_id: int, 
    updated_quote_data: QuoteUpdate, 
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Update an existing quote (Admin only)
    """
    # Quote update
    quote = db.query(Quote).filter(Quote.id == quote_id, Quote.is_active == True).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    # Update only provided fields
    update_data = updated_quote_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(quote, field, value)
    
    db.commit()
    db.refresh(quote)
    
    return quote

def remove_quote(
    quote_id: int, 
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Soft delete a quote (Admin only)
    """
    # Soft delete
    quote = db.query(Quote).filter(Quote.id == quote_id, Quote.is_active == True).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    quote.is_active = False
    db.commit()
    
    return SuccessResponse(message="Quote successfully marked as inactive")