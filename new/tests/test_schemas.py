"""
Tests for Pydantic schema validation.
Verifies input validation, edge cases, and error handling.
"""

import pytest
from datetime import date

from app.schemas import (
    InjuryHistoryItem,
    UserProfile,
    WorkoutRequest,
    Exercise,
    WorkoutPlan,
    Critique,
    PlanResponse,
    HealthResponse,
)


# ============= UserProfile Tests ============= #


class TestUserProfile:
    """Tests for UserProfile schema validation."""

    def test_valid_profile(self):
        profile = UserProfile(
            goals="Build upper body strength",
            fitness_level="intermediate",
            weight=75.0,
            age=28,
            equipment_available=["barbell", "dumbbells"],
        )
        assert profile.goals == "Build upper body strength"
        assert profile.fitness_level == "intermediate"
        assert profile.weight == 75.0

    def test_valid_profile_minimal(self):
        """Only required fields."""
        profile = UserProfile(
            goals="Get fit and healthy",
            fitness_level="beginner",
        )
        assert profile.weight is None
        assert profile.age is None
        assert profile.equipment_available == []

    def test_goals_too_short(self):
        with pytest.raises(ValueError, match="at least 5 characters"):
            UserProfile(goals="Hi", fitness_level="beginner")

    def test_goals_whitespace_stripped(self):
        profile = UserProfile(
            goals="   Build muscle and strength   ",
            fitness_level="advanced",
        )
        assert profile.goals == "Build muscle and strength"

    def test_invalid_fitness_level(self):
        with pytest.raises(ValueError):
            UserProfile(goals="Build strength", fitness_level="superhuman")

    def test_invalid_weight_zero(self):
        with pytest.raises(ValueError):
            UserProfile(
                goals="Build strength",
                fitness_level="beginner",
                weight=0,
            )

    def test_invalid_weight_negative(self):
        with pytest.raises(ValueError):
            UserProfile(
                goals="Build strength",
                fitness_level="beginner",
                weight=-10,
            )

    def test_invalid_age_too_high(self):
        with pytest.raises(ValueError):
            UserProfile(
                goals="Maintain fitness",
                fitness_level="beginner",
                age=150,
            )

    def test_invalid_age_zero(self):
        with pytest.raises(ValueError):
            UserProfile(
                goals="Maintain fitness",
                fitness_level="beginner",
                age=0,
            )


# ============= InjuryHistoryItem Tests ============= #


class TestInjuryHistoryItem:
    """Tests for InjuryHistoryItem schema."""

    def test_valid_injury(self):
        injury = InjuryHistoryItem(
            injury_type="Rotator cuff strain",
            injury_date=date(2024, 3, 15),
            severity="moderate",
            notes="Avoid overhead press",
        )
        assert injury.injury_type == "Rotator cuff strain"
        assert injury.severity == "moderate"

    def test_valid_injury_no_notes(self):
        injury = InjuryHistoryItem(
            injury_type="Knee tendonitis",
            injury_date=date(2024, 1, 1),
            severity="minor",
        )
        assert injury.notes is None

    def test_invalid_severity(self):
        with pytest.raises(ValueError):
            InjuryHistoryItem(
                injury_type="Back pain",
                injury_date=date(2024, 1, 1),
                severity="extreme",
            )

    def test_all_severity_levels(self):
        for level in ["minor", "moderate", "severe"]:
            injury = InjuryHistoryItem(
                injury_type="Test injury",
                injury_date=date(2024, 1, 1),
                severity=level,
            )
            assert injury.severity == level


# ============= WorkoutRequest Tests ============= #


class TestWorkoutRequest:
    """Tests for WorkoutRequest schema."""

    def test_valid_request(self):
        request = WorkoutRequest(
            user_profile=UserProfile(
                goals="Build strength",
                fitness_level="intermediate",
            ),
            injury_history=[],
            thread_id="user_123",
        )
        assert request.thread_id == "user_123"
        assert request.injury_history == []

    def test_request_with_injuries(self):
        request = WorkoutRequest(
            user_profile=UserProfile(
                goals="General fitness",
                fitness_level="beginner",
            ),
            injury_history=[
                InjuryHistoryItem(
                    injury_type="ACL tear",
                    injury_date=date(2023, 6, 1),
                    severity="severe",
                )
            ],
            thread_id="user_456",
        )
        assert len(request.injury_history) == 1

    def test_missing_thread_id(self):
        with pytest.raises(ValueError):
            WorkoutRequest(
                user_profile=UserProfile(
                    goals="Get fit for summer",
                    fitness_level="beginner",
                ),
            )


# ============= Output Schema Tests ============= #


class TestExercise:
    """Tests for Exercise output schema."""

    def test_valid_exercise(self):
        ex = Exercise(
            name="Bench Press",
            sets=3,
            reps="8-12",
            weight_kg=60.0,
            rest_seconds=90,
            notes="Control the eccentric",
        )
        assert ex.name == "Bench Press"
        assert ex.sets == 3

    def test_invalid_sets_zero(self):
        with pytest.raises(ValueError):
            Exercise(name="Squat", sets=0, reps="10")

    def test_minimal_exercise(self):
        ex = Exercise(name="Push-up", sets=3, reps="15")
        assert ex.weight_kg is None
        assert ex.rest_seconds is None
        assert ex.notes is None


class TestCritique:
    """Tests for Critique output schema."""

    def test_safe_critique(self):
        critique = Critique(
            status="SAFE",
            feedback="Plan looks good.",
            flagged_exercises=[],
        )
        assert critique.status == "SAFE"

    def test_unsafe_critique(self):
        critique = Critique(
            status="UNSAFE",
            feedback="Overhead press risky for rotator cuff.",
            flagged_exercises=["Overhead Press"],
        )
        assert critique.status == "UNSAFE"
        assert len(critique.flagged_exercises) == 1

    def test_invalid_status(self):
        with pytest.raises(ValueError):
            Critique(status="MAYBE", feedback="Not sure")


class TestHealthResponse:
    """Tests for HealthResponse schema."""

    def test_healthy(self):
        resp = HealthResponse(
            status="healthy",
            database="connected",
            llm_provider="ollama",
        )
        assert resp.status == "healthy"

    def test_unhealthy(self):
        resp = HealthResponse(
            status="unhealthy",
            database="disconnected",
            llm_provider="none",
        )
        assert resp.status == "unhealthy"

    def test_invalid_status(self):
        with pytest.raises(ValueError):
            HealthResponse(
                status="unknown",
                database="connected",
                llm_provider="ollama",
            )
