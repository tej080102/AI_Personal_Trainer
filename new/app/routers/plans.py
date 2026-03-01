"""
Workout Plan History API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import logging

from ..database import get_db
from ..models import User, WorkoutPlan
from .auth import require_auth

router = APIRouter(prefix="/plans", tags=["Workout Plans"])
logger = logging.getLogger(__name__)


# ============= Pydantic Schemas ============= #

class PlanCreate(BaseModel):
    """Create plan entry."""
    plan_name: str
    plan_data: dict
    critique_data: Optional[dict] = None
    revision_count: int = 1
    safety_status: str
    goals: Optional[str] = None
    total_latency_ms: Optional[int] = None
    llm_calls: Optional[int] = None
    tokens_estimated: Optional[int] = None


class PlanResponse(BaseModel):
    """Plan response."""
    id: int
    plan_name: str
    plan_data: dict
    critique_data: Optional[dict]
    revision_count: int
    safety_status: str
    goals: Optional[str]
    created_at: datetime
    total_latency_ms: Optional[int]
    llm_calls: Optional[int]
    tokens_estimated: Optional[int]
    
    class Config:
        from_attributes = True


class PlanSummary(BaseModel):
    """Plan summary for list view."""
    id: int
    plan_name: str
    safety_status: str
    revision_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============= Endpoints ============= #

@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def save_plan(
    plan: PlanCreate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Save a generated workout plan."""
    db_plan = WorkoutPlan(
        user_id=current_user.id,
        plan_name=plan.plan_name,
        plan_data=plan.plan_data,
        critique_data=plan.critique_data,
        revision_count=plan.revision_count,
        safety_status=plan.safety_status,
        goals=plan.goals,
        total_latency_ms=plan.total_latency_ms,
        llm_calls=plan.llm_calls,
        tokens_estimated=plan.tokens_estimated
    )
    
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    
    logger.info(f"Plan saved: {plan.plan_name} for user {current_user.username}")
    return db_plan


@router.get("", response_model=List[PlanSummary])
def get_plans(
    limit: int = 50,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get user's saved workout plans (summary view)."""
    plans = db.query(WorkoutPlan).filter(
        WorkoutPlan.user_id == current_user.id
    ).order_by(WorkoutPlan.created_at.desc()).limit(limit).all()
    
    return plans


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(
    plan_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get a specific workout plan with full details."""
    plan = db.query(WorkoutPlan).filter(
        WorkoutPlan.id == plan_id,
        WorkoutPlan.user_id == current_user.id
    ).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(
    plan_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Delete a workout plan."""
    plan = db.query(WorkoutPlan).filter(
        WorkoutPlan.id == plan_id,
        WorkoutPlan.user_id == current_user.id
    ).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    db.delete(plan)
    db.commit()
    
    logger.info(f"Plan deleted: {plan_id} for user {current_user.username}")


@router.get("/stats/summary")
def get_plan_stats(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get statistics about generated plans."""
    from sqlalchemy import func
    
    total = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == current_user.id).count()
    
    safe_count = db.query(WorkoutPlan).filter(
        WorkoutPlan.user_id == current_user.id,
        WorkoutPlan.safety_status == "SAFE"
    ).count()
    
    avg_revisions = db.query(func.avg(WorkoutPlan.revision_count)).filter(
        WorkoutPlan.user_id == current_user.id
    ).scalar() or 0
    
    avg_latency = db.query(func.avg(WorkoutPlan.total_latency_ms)).filter(
        WorkoutPlan.user_id == current_user.id
    ).scalar() or 0
    
    return {
        "total_plans": total,
        "safe_plans": safe_count,
        "safety_triggered": total - safe_count if total > 0 else 0,
        "avg_revisions": round(avg_revisions, 2),
        "avg_latency_ms": int(avg_latency)
    }
