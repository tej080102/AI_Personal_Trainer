"""
Tests for LangGraph workflow logic.
Tests state initialization and routing decisions.
No LLM or database required.

Skipped if langgraph is not fully installed (e.g. missing checkpoint extras).
"""

import pytest

try:
    from app.graph import initialize_state, route_after_critique
    HAS_LANGGRAPH = True
except (ImportError, ModuleNotFoundError):
    HAS_LANGGRAPH = False

pytestmark = pytest.mark.skipif(
    not HAS_LANGGRAPH,
    reason="langgraph not fully installed (missing checkpoint dependencies)"
)


# ============= State Initialization Tests ============= #


class TestInitializeState:
    """Tests for initialize_state helper."""

    def test_basic_state(self, sample_user_profile, sample_injury_history):
        state = initialize_state(
            user_profile=sample_user_profile,
            injury_history=sample_injury_history,
            thread_id="test_001",
        )
        assert state["user_profile"] == sample_user_profile
        assert state["injury_history"] == sample_injury_history
        assert state["thread_id"] == "test_001"
        assert state["revision_count"] == 0
        assert state["workout_plan"] is None
        assert state["critique"] is None
        assert state["messages"] == []

    def test_no_injuries(self, sample_user_profile):
        state = initialize_state(
            user_profile=sample_user_profile,
            injury_history=[],
            thread_id="test_002",
        )
        assert state["injury_history"] == []

    def test_thread_id_preserved(self, sample_user_profile):
        state = initialize_state(
            user_profile=sample_user_profile,
            injury_history=[],
            thread_id="my_unique_session_xyz",
        )
        assert state["thread_id"] == "my_unique_session_xyz"


# ============= Routing Logic Tests ============= #


class TestRouteAfterCritique:
    """Tests for the conditional routing function."""

    def test_safe_plan_ends(self, sample_user_profile):
        """SAFE critique should route to END."""
        state = {
            "user_profile": sample_user_profile,
            "injury_history": [],
            "workout_plan": {"name": "Test Plan"},
            "critique": {"status": "SAFE", "feedback": "Good", "flagged_exercises": []},
            "revision_count": 1,
            "thread_id": "test",
            "messages": [],
        }
        result = route_after_critique(state)
        assert result == "__end__"

    def test_unsafe_plan_loops_back(self, sample_user_profile):
        """UNSAFE critique with low revision count should loop back."""
        state = {
            "user_profile": sample_user_profile,
            "injury_history": [],
            "workout_plan": {"name": "Test Plan"},
            "critique": {
                "status": "UNSAFE",
                "feedback": "Overhead press is dangerous",
                "flagged_exercises": ["Overhead Press"],
            },
            "revision_count": 1,
            "thread_id": "test",
            "messages": [],
        }
        result = route_after_critique(state)
        assert result == "draft_plan"

    def test_unsafe_but_max_revisions_ends(self, sample_user_profile):
        """UNSAFE but at max revisions (3) should end anyway."""
        state = {
            "user_profile": sample_user_profile,
            "injury_history": [],
            "workout_plan": {"name": "Test Plan"},
            "critique": {
                "status": "UNSAFE",
                "feedback": "Still risky",
                "flagged_exercises": ["Squat"],
            },
            "revision_count": 3,
            "thread_id": "test",
            "messages": [],
        }
        result = route_after_critique(state)
        assert result == "__end__"

    def test_no_critique_ends(self, sample_user_profile):
        """Missing critique should route to end."""
        state = {
            "user_profile": sample_user_profile,
            "injury_history": [],
            "workout_plan": {"name": "Test Plan"},
            "critique": None,
            "revision_count": 1,
            "thread_id": "test",
            "messages": [],
        }
        result = route_after_critique(state)
        assert result == "__end__"
