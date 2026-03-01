"""
Tests for prompt template generation.
Verifies prompts include correct context, injury info, and revision guidance.
No LLM required.
"""

import pytest

from app.prompts import (
    DRAFT_PLAN_SYSTEM_PROMPT,
    CRITIQUE_SYSTEM_PROMPT,
    get_draft_plan_prompt,
    get_critique_prompt,
)


# ============= System Prompt Tests ============= #


class TestSystemPrompts:
    """Verify system prompts contain expected content."""

    def test_draft_system_prompt_has_trainer_role(self):
        assert "personal trainer" in DRAFT_PLAN_SYSTEM_PROMPT.lower()

    def test_critique_system_prompt_has_physio_role(self):
        assert "physiotherapist" in CRITIQUE_SYSTEM_PROMPT.lower()

    def test_critique_system_prompt_mentions_safety(self):
        assert "safety" in CRITIQUE_SYSTEM_PROMPT.lower()


# ============= Draft Plan Prompt Tests ============= #


class TestDraftPlanPrompt:
    """Tests for get_draft_plan_prompt."""

    def test_includes_user_goals(self, sample_user_profile):
        prompt = get_draft_plan_prompt(sample_user_profile, [])
        assert sample_user_profile["goals"] in prompt

    def test_includes_fitness_level(self, sample_user_profile):
        prompt = get_draft_plan_prompt(sample_user_profile, [])
        assert sample_user_profile["fitness_level"] in prompt

    def test_includes_equipment(self, sample_user_profile):
        prompt = get_draft_plan_prompt(sample_user_profile, [])
        for equip in sample_user_profile["equipment_available"]:
            assert equip in prompt

    def test_no_injuries_says_none(self, sample_user_profile):
        prompt = get_draft_plan_prompt(sample_user_profile, [])
        assert "None reported" in prompt

    def test_includes_injury_details(self, sample_user_profile, sample_injury_history):
        prompt = get_draft_plan_prompt(sample_user_profile, sample_injury_history)
        assert "Rotator cuff strain" in prompt
        assert "moderate" in prompt

    def test_includes_json_format_instructions(self, sample_user_profile):
        prompt = get_draft_plan_prompt(sample_user_profile, [])
        assert "JSON" in prompt
        assert '"name"' in prompt
        assert '"exercises"' in prompt

    def test_revision_includes_critique_feedback(
        self, sample_user_profile, sample_injury_history, unsafe_critique
    ):
        prompt = get_draft_plan_prompt(
            sample_user_profile, sample_injury_history, critique=unsafe_critique
        )
        assert "REVISION REQUIRED" in prompt
        assert unsafe_critique["feedback"] in prompt

    def test_revision_lists_flagged_exercises(
        self, sample_user_profile, unsafe_critique
    ):
        prompt = get_draft_plan_prompt(
            sample_user_profile, [], critique=unsafe_critique
        )
        for ex in unsafe_critique["flagged_exercises"]:
            assert ex in prompt

    def test_safe_critique_no_revision_block(
        self, sample_user_profile, safe_critique
    ):
        prompt = get_draft_plan_prompt(
            sample_user_profile, [], critique=safe_critique
        )
        assert "REVISION REQUIRED" not in prompt


# ============= Critique Prompt Tests ============= #


class TestCritiquePrompt:
    """Tests for get_critique_prompt."""

    def test_includes_workout_plan_name(self, sample_workout_plan):
        prompt = get_critique_prompt(sample_workout_plan, [])
        assert sample_workout_plan["name"] in prompt

    def test_includes_exercises(self, sample_workout_plan):
        prompt = get_critique_prompt(sample_workout_plan, [])
        for ex in sample_workout_plan["exercises"]:
            assert ex["name"] in prompt

    def test_includes_injury_context(self, sample_workout_plan, sample_injury_history):
        prompt = get_critique_prompt(sample_workout_plan, sample_injury_history)
        assert "Rotator cuff strain" in prompt
        assert "moderate" in prompt

    def test_no_injuries_says_none(self, sample_workout_plan):
        prompt = get_critique_prompt(sample_workout_plan, [])
        assert "None reported" in prompt

    def test_asks_for_json_response(self, sample_workout_plan):
        prompt = get_critique_prompt(sample_workout_plan, [])
        assert "JSON" in prompt
        assert '"status"' in prompt
        assert "SAFE" in prompt
        assert "UNSAFE" in prompt

    def test_mentions_decision_criteria(self, sample_workout_plan):
        prompt = get_critique_prompt(sample_workout_plan, [])
        assert "Decision Criteria" in prompt
