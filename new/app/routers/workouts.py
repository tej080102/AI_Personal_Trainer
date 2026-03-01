"""
Workout Management API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date
import logging
import json

from ..database import get_db
from ..models import User, Workout
from .auth import require_auth, get_current_user

router = APIRouter(prefix="/workouts", tags=["Workouts"])
logger = logging.getLogger(__name__)


# ============= Pydantic Schemas ============= #

class WorkoutCreate(BaseModel):
    """Create workout entry."""
    date: date
    exercise: str
    sets: Optional[int] = None
    reps: Optional[str] = None  # Can be "10" or "[10,8,6]"
    weight: Optional[float] = None
    distance: Optional[float] = None
    duration: Optional[float] = None
    notes: Optional[str] = None


class WorkoutResponse(BaseModel):
    """Workout response."""
    id: int
    date: datetime
    exercise: str
    sets: Optional[int]
    reps: Optional[str]
    weight: Optional[float]
    distance: Optional[float]
    duration: Optional[float]
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class WorkoutStats(BaseModel):
    """Workout statistics."""
    total_workouts: int
    this_week: int
    total_volume_kg: float
    total_distance_km: float
    current_streak: int
    exercises_count: int


class ParseWorkoutRequest(BaseModel):
    """Request to parse natural language workout."""
    text: str


# ============= Endpoints ============= #

@router.post("", response_model=WorkoutResponse, status_code=status.HTTP_201_CREATED)
def create_workout(
    workout: WorkoutCreate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Create a new workout entry."""
    db_workout = Workout(
        user_id=current_user.id,
        date=datetime.combine(workout.date, datetime.min.time()),
        exercise=workout.exercise,
        sets=workout.sets,
        reps=workout.reps,
        weight=workout.weight,
        distance=workout.distance,
        duration=workout.duration,
        notes=workout.notes
    )
    
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    
    logger.info(f"Workout logged: {workout.exercise} by user {current_user.username}")
    return db_workout


@router.post("/batch", response_model=List[WorkoutResponse], status_code=status.HTTP_201_CREATED)
def create_workouts_batch(
    workouts: List[WorkoutCreate],
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Create multiple workout entries (for LLM-parsed results)."""
    created = []
    
    for workout in workouts:
        db_workout = Workout(
            user_id=current_user.id,
            date=datetime.combine(workout.date, datetime.min.time()),
            exercise=workout.exercise,
            sets=workout.sets,
            reps=workout.reps,
            weight=workout.weight,
            distance=workout.distance,
            duration=workout.duration,
            notes=workout.notes
        )
        db.add(db_workout)
        created.append(db_workout)
    
    db.commit()
    
    for w in created:
        db.refresh(w)
    
    logger.info(f"Batch logged: {len(created)} workouts by user {current_user.username}")
    return created


@router.get("", response_model=List[WorkoutResponse])
def get_workouts(
    limit: int = 100,
    offset: int = 0,
    exercise: Optional[str] = None,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get user's workout history."""
    query = db.query(Workout).filter(Workout.user_id == current_user.id)
    
    if exercise:
        query = query.filter(func.lower(Workout.exercise) == exercise.lower())
    
    workouts = query.order_by(Workout.date.desc(), Workout.id.desc())\
                    .offset(offset)\
                    .limit(limit)\
                    .all()
    
    return workouts


@router.get("/stats", response_model=WorkoutStats)
def get_workout_stats(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get workout statistics for dashboard."""
    from datetime import timedelta
    
    # Total workouts
    total = db.query(Workout).filter(Workout.user_id == current_user.id).count()
    
    # This week
    week_ago = datetime.utcnow() - timedelta(days=7)
    this_week = db.query(Workout).filter(
        Workout.user_id == current_user.id,
        Workout.date >= week_ago
    ).count()
    
    # Total volume (sets * reps * weight approximation)
    workouts = db.query(Workout).filter(
        Workout.user_id == current_user.id,
        Workout.weight.isnot(None)
    ).all()
    
    total_volume = 0
    for w in workouts:
        if w.weight and w.sets:
            reps = 10  # Default
            if w.reps:
                try:
                    reps_data = json.loads(w.reps) if w.reps.startswith('[') else int(w.reps)
                    if isinstance(reps_data, list):
                        reps = sum(reps_data)
                    else:
                        reps = reps_data
                except:
                    pass
            total_volume += w.sets * reps * w.weight
    
    # Total distance
    total_distance = db.query(func.sum(Workout.distance)).filter(
        Workout.user_id == current_user.id
    ).scalar() or 0
    
    # Current streak (consecutive days with workouts)
    dates = db.query(func.date(Workout.date)).filter(
        Workout.user_id == current_user.id
    ).distinct().order_by(func.date(Workout.date).desc()).limit(30).all()
    
    streak = 0
    if dates:
        today = date.today()
        for i, (d,) in enumerate(dates):
            expected = today - timedelta(days=i)
            if d == expected:
                streak += 1
            else:
                break
    
    # Unique exercises
    exercises = db.query(func.count(func.distinct(Workout.exercise))).filter(
        Workout.user_id == current_user.id
    ).scalar() or 0
    
    return WorkoutStats(
        total_workouts=total,
        this_week=this_week,
        total_volume_kg=total_volume,
        total_distance_km=total_distance,
        current_streak=streak,
        exercises_count=exercises
    )


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(
    workout_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Delete a workout entry."""
    workout = db.query(Workout).filter(
        Workout.id == workout_id,
        Workout.user_id == current_user.id
    ).first()
    
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    db.delete(workout)
    db.commit()
    
    logger.info(f"Workout deleted: {workout_id} by user {current_user.username}")


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_all_workouts(
    exercise: Optional[str] = None,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Clear all workouts or by exercise type."""
    query = db.query(Workout).filter(Workout.user_id == current_user.id)
    
    if exercise:
        query = query.filter(func.lower(Workout.exercise) == exercise.lower())
    
    count = query.delete()
    db.commit()
    
    logger.info(f"Cleared {count} workouts for user {current_user.username}")
