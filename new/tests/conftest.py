"""
Shared pytest fixtures for AI Personal Trainer tests.
"""

import pytest


@pytest.fixture
def sample_user_profile():
    """Standard user profile for testing."""
    return {
        "goals": "Build upper body strength and muscle mass",
        "fitness_level": "intermediate",
        "weight": 75.0,
        "age": 28,
        "equipment_available": ["barbell", "dumbbells", "bench"],
    }


@pytest.fixture
def sample_injury_history():
    """User with a rotator cuff injury."""
    return [
        {
            "injury_type": "Rotator cuff strain",
            "injury_date": "2024-03-15",
            "severity": "moderate",
            "notes": "Avoid overhead press for 6 weeks",
        }
    ]


@pytest.fixture
def sample_workout_plan():
    """A valid workout plan dict (as returned by LLM)."""
    return {
        "name": "Upper Body Strength - Week 1",
        "frequency": "3x per week",
        "exercises": [
            {
                "name": "Bench Press",
                "sets": 4,
                "reps": "8-10",
                "weight_kg": 60.0,
                "rest_seconds": 90,
                "notes": "Flat bench, controlled eccentric",
            },
            {
                "name": "Dumbbell Row",
                "sets": 3,
                "reps": "10-12",
                "weight_kg": 25.0,
                "rest_seconds": 60,
                "notes": "Squeeze at top",
            },
        ],
        "warm_up": "5 min light cardio + dynamic stretches",
        "cool_down": "Static stretching for 5-10 min",
        "progression_notes": "Increase weight by 2.5kg when all sets hit top rep range",
    }


@pytest.fixture
def safe_critique():
    """A SAFE critique result."""
    return {
        "status": "SAFE",
        "feedback": "All exercises are appropriate for the user's injury history.",
        "flagged_exercises": [],
    }


@pytest.fixture
def unsafe_critique():
    """An UNSAFE critique result."""
    return {
        "status": "UNSAFE",
        "feedback": "Overhead press is contraindicated for rotator cuff strain.",
        "flagged_exercises": ["Overhead Press", "Military Press"],
    }
