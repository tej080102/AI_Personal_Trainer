"""
Injury Profile Management API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date
import logging

from ..database import get_db
from ..models import User, Injury
from .auth import require_auth

router = APIRouter(prefix="/injuries", tags=["Injuries"])
logger = logging.getLogger(__name__)


# ============= Pydantic Schemas ============= #

class InjuryCreate(BaseModel):
    """Create injury entry."""
    injury_type: str
    injury_date: date
    severity: str  # mild, moderate, severe
    notes: Optional[str] = None
    is_active: bool = True


class InjuryUpdate(BaseModel):
    """Update injury entry."""
    injury_type: Optional[str] = None
    injury_date: Optional[date] = None
    severity: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class InjuryResponse(BaseModel):
    """Injury response."""
    id: int
    injury_type: str
    injury_date: datetime
    severity: str
    notes: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============= Endpoints ============= #

@router.post("", response_model=InjuryResponse, status_code=status.HTTP_201_CREATED)
def create_injury(
    injury: InjuryCreate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Add a new injury to profile."""
    if injury.severity not in ["mild", "moderate", "severe"]:
        raise HTTPException(
            status_code=400,
            detail="Severity must be 'mild', 'moderate', or 'severe'"
        )
    
    db_injury = Injury(
        user_id=current_user.id,
        injury_type=injury.injury_type,
        injury_date=datetime.combine(injury.injury_date, datetime.min.time()),
        severity=injury.severity,
        notes=injury.notes,
        is_active=injury.is_active
    )
    
    db.add(db_injury)
    db.commit()
    db.refresh(db_injury)
    
    logger.info(f"Injury added: {injury.injury_type} for user {current_user.username}")
    return db_injury


@router.get("", response_model=List[InjuryResponse])
def get_injuries(
    active_only: bool = False,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get user's injury history."""
    query = db.query(Injury).filter(Injury.user_id == current_user.id)
    
    if active_only:
        query = query.filter(Injury.is_active == True)
    
    injuries = query.order_by(Injury.injury_date.desc()).all()
    return injuries


@router.get("/active", response_model=List[InjuryResponse])
def get_active_injuries(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get only active injuries (for workout plan generation)."""
    injuries = db.query(Injury).filter(
        Injury.user_id == current_user.id,
        Injury.is_active == True
    ).order_by(Injury.injury_date.desc()).all()
    
    return injuries


@router.patch("/{injury_id}", response_model=InjuryResponse)
def update_injury(
    injury_id: int,
    injury_update: InjuryUpdate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Update an injury entry."""
    injury = db.query(Injury).filter(
        Injury.id == injury_id,
        Injury.user_id == current_user.id
    ).first()
    
    if not injury:
        raise HTTPException(status_code=404, detail="Injury not found")
    
    if injury_update.injury_type is not None:
        injury.injury_type = injury_update.injury_type
    if injury_update.injury_date is not None:
        injury.injury_date = datetime.combine(injury_update.injury_date, datetime.min.time())
    if injury_update.severity is not None:
        if injury_update.severity not in ["mild", "moderate", "severe"]:
            raise HTTPException(status_code=400, detail="Invalid severity")
        injury.severity = injury_update.severity
    if injury_update.notes is not None:
        injury.notes = injury_update.notes
    if injury_update.is_active is not None:
        injury.is_active = injury_update.is_active
    
    db.commit()
    db.refresh(injury)
    
    logger.info(f"Injury updated: {injury_id} for user {current_user.username}")
    return injury


@router.delete("/{injury_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_injury(
    injury_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Delete an injury from profile."""
    injury = db.query(Injury).filter(
        Injury.id == injury_id,
        Injury.user_id == current_user.id
    ).first()
    
    if not injury:
        raise HTTPException(status_code=404, detail="Injury not found")
    
    db.delete(injury)
    db.commit()
    
    logger.info(f"Injury deleted: {injury_id} for user {current_user.username}")
