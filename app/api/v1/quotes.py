from fastapi import HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.core.database import get_db
from app.models.quotes import Quote
from app.schemas.quote import QuoteResponse, QuoteListResponse

def get_random_quote(
    db: Session = Depends(get_db)
):
    """
    Get a random motivational quote for home page popup (Public endpoint)
    """
    # Random quote query
    quote = db.query(Quote).filter(Quote.is_active == True).order_by(func.random()).first()
    
    if not quote:
        raise HTTPException(status_code=404, detail="No motivational quotes available")
    
    return quote

def get_quotes_list(
    skip: int = Query(0, ge=0, description="Number of quotes to skip"), 
    limit: int = Query(10, ge=1, le=50, description="Maximum number of quotes to return"),
    db: Session = Depends(get_db)
):
    """
    Get a limited list of active quotes for public viewing
    """
    # Database query
    quotes = db.query(Quote).filter(Quote.is_active == True).offset(skip).limit(limit).all()
    
    # Get total count for pagination
    total = db.query(Quote).filter(Quote.is_active == True).count()
    
    return QuoteListResponse(
        quotes=quotes,
        total=total,
        page=skip // limit + 1,
        limit=limit
    )
