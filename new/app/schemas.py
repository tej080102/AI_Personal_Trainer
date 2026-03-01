"""
Pydantic Models for API Input/Output Validation
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import date


# ============= Input Models ============= #

class InjuryHistoryItem(BaseModel):
    """Structured injury data for safety analysis."""
    injury_type: str = Field(..., description="Type of injury (e.g., 'Rotator cuff strain', 'Knee tendonitis')")
    injury_date: date = Field(..., description="When the injury occurred")
    severity: Literal["minor", "moderate", "severe"] = Field(..., description="Injury severity level")
    notes: Optional[str] = Field(None, description="Additional context about the injury")


class UserProfile(BaseModel):
    """User fitness profile and goals."""
    goals: str = Field(..., description="Fitness goals (e.g., 'Build upper body strength', 'Train for marathon')")
    fitness_level: Literal["beginner", "intermediate", "advanced"] = Field(..., description="Current fitness level")
    weight: Optional[float] = Field(None, description="Body weight in kg", gt=0)
    age: Optional[int] = Field(None, description="Age in years", gt=0, lt=120)
    equipment_available: Optional[list[str]] = Field(default_factory=list, description="Available equipment")
    
    @field_validator('goals')
    @classmethod
    def validate_goals(cls, v):
        if len(v.strip()) < 5:
            raise ValueError("Goals must be at least 5 characters")
        return v.strip()


class WorkoutRequest(BaseModel):
    """Request to generate a workout plan."""
    user_profile: UserProfile
    injury_history: list[InjuryHistoryItem] = Field(default_factory=list)
    thread_id: str = Field(..., description="Session identifier for persistence")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_profile": {
                        "goals": "Build upper body strength and muscle mass",
                        "fitness_level": "intermediate",
                        "weight": 75.0,
                        "age": 28,
                        "equipment_available": ["barbell", "dumbbells", "bench"]
                    },
                    "injury_history": [
                        {
                            "injury_type": "Rotator cuff strain",
                            "injury_date": "2024-03-15",
                            "severity": "moderate",
                            "notes": "Avoid overhead movements for 6 weeks"
                        }
                    ],
                    "thread_id": "user_12345"
                }
            ]
        }
    }


# ============= Output Models ============= #

class Exercise(BaseModel):
    """Single exercise in a workout plan."""
    name: str
    sets: int = Field(..., gt=0)
    reps: str  # Can be "8-12" or "10" or list like "10,8,6"
    weight_kg: Optional[float] = Field(None, description="Recommended weight in kg")
    rest_seconds: Optional[int] = Field(None, description="Rest between sets")
    notes: Optional[str] = Field(None, description="Form cues or modifications")

    @field_validator('reps', mode='before')
    @classmethod
    def coerce_reps_to_str(cls, v):
        """LLMs sometimes return reps as int instead of str."""
        if v is not None:
            return str(v)
        return v

    @field_validator('sets', mode='before')
    @classmethod
    def coerce_sets_to_int(cls, v):
        """LLMs sometimes return sets as str instead of int."""
        if isinstance(v, str):
            return int(v)
        return v


class WorkoutPlan(BaseModel):
    """Complete workout plan with exercises and schedule."""
    name: str = Field(..., description="Plan name (e.g., 'Upper Body Strength - Week 1')")
    frequency: str = Field(..., description="Training frequency (e.g., '3x per week')")
    exercises: list[Exercise]
    warm_up: Optional[str] = Field(None, description="Warm-up routine")
    cool_down: Optional[str] = Field(None, description="Cool-down routine")
    progression_notes: Optional[str] = Field(None, description="How to progress over time")


class Critique(BaseModel):
    """Safety critique from physiotherapist agent."""
    status: Literal["SAFE", "UNSAFE"]
    feedback: str = Field(..., description="Specific safety concerns or approval")
    flagged_exercises: Optional[list[str]] = Field(default_factory=list, description="Exercises that conflict with injuries")


class PlanResponse(BaseModel):
    """Complete response from the plan generation endpoint."""
    workout_plan: WorkoutPlan
    critique: Critique
    revision_count: int = Field(..., description="Number of revisions made")
    thread_id: str


# ============= History Models ============= #

class StateHistoryItem(BaseModel):
    """Single state from conversation history."""
    timestamp: str
    workout_plan: Optional[WorkoutPlan]
    critique: Optional[Critique]
    revision_count: int


class HistoryResponse(BaseModel):
    """Response from history endpoint."""
    thread_id: str
    history: list[StateHistoryItem]


# ============= Health Check ============= #

class HealthResponse(BaseModel):
    """Health check response."""
    status: Literal["healthy", "unhealthy"]
    database: Literal["connected", "disconnected"]
    llm_provider: str
