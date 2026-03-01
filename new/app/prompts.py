"""
Centralized Prompt Templates
Maintains all LLM prompts for version control and A/B testing.
"""

# ============= Workout Plan Drafting ============= #

DRAFT_PLAN_SYSTEM_PROMPT = """You are an expert personal trainer with 15+ years of experience in strength training, hypertrophy, and athletic performance.

Your expertise includes:
- Periodization and progressive overload
- Exercise selection based on equipment and experience level
- Rep ranges and intensity for different goals
- Recovery and training frequency

You create science-based, practical workout plans tailored to individual needs."""


def get_draft_plan_prompt(user_profile: dict, injury_history: list[dict], critique: dict = None) -> str:
    """
    Generate the prompt for drafting a workout plan.
    
    Args:
        user_profile: User's goals, fitness level, equipment
        injury_history: List of past injuries
        critique: If this is a revision, the physiotherapist's feedback
    
    Returns:
        Complete prompt for the trainer LLM
    """
    
    # Format injury history for readability
    injury_text = "None reported" if not injury_history else "\n".join([
        f"- {inj['injury_type']} on {inj.get('injury_date', 'unknown date')} (Severity: {inj['severity']})"
        + (f"\n  Notes: {inj['notes']}" if inj.get('notes') else "")
        for inj in injury_history
    ])
    
    # Base prompt
    prompt = f"""Create a detailed workout plan for a user with the following profile:

**Goals:** {user_profile.get('goals', 'General fitness')}
**Fitness Level:** {user_profile.get('fitness_level', 'beginner')}
**Weight:** {user_profile.get('weight', 'Not provided')} kg
**Age:** {user_profile.get('age', 'Not provided')}
**Equipment Available:** {', '.join(user_profile.get('equipment_available', ['None specified']))}

**Injury History:**
{injury_text}
"""
    
    # Add revision guidance if this is a critique loop
    if critique and critique.get('status') == 'UNSAFE':
        prompt += f"""

⚠️ **IMPORTANT - REVISION REQUIRED:**
The previous plan was flagged as UNSAFE by our physiotherapist. You MUST address the following concerns:

{critique.get('feedback', 'No specific feedback')}

**Flagged Exercises:** {', '.join(critique.get('flagged_exercises', []))}

Please revise the plan to:
1. Remove or modify the flagged exercises
2. Replace them with safer alternatives that still meet the user's goals
3. Ensure all movements are compatible with the injury history
"""
    
    # Output format instructions
    prompt += """

Return ONLY a valid JSON object with this exact structure (no markdown, no extra text):

{
    "name": "Plan name (e.g., 'Upper Body Hypertrophy - Week 1')",
    "frequency": "Training frequency (e.g., '3x per week', 'Mon/Wed/Fri')",
    "exercises": [
        {
            "name": "Exercise name",
            "sets": 3,
            "reps": "8-12",
            "weight_kg": 50.0,
            "rest_seconds": 90,
            "notes": "Form cues or modifications"
        }
    ],
    "warm_up": "5-10 min dynamic stretching, light cardio",
    "cool_down": "Stretch major muscle groups for 5-10 min",
    "progression_notes": "Increase weight by 2.5kg when all sets hit top rep range"
}

Ensure the plan is:
- Specific to the user's goals
- Appropriate for their fitness level
- Compatible with their injury history
- Balanced and sustainable
"""
    
    return prompt


# ============= Safety Critique ============= #

CRITIQUE_SYSTEM_PROMPT = """You are a licensed physiotherapist specializing in sports medicine and injury prevention with 20+ years of clinical experience.

Your role is to review workout plans and identify potential injury risks, especially for clients with existing injuries or movement limitations.

You are NOT a trainer trying to design workouts. You are ONLY a safety reviewer who:
- Analyzes biomechanics and joint stress
- Identifies contraindicated movements for specific injuries
- Suggests safer alternatives when needed
- Approves safe plans without unnecessary changes

Be conservative with safety but practical with recommendations."""


def get_critique_prompt(workout_plan: dict, injury_history: list[dict]) -> str:
    """
    Generate the prompt for safety critique.
    
    Args:
        workout_plan: The drafted workout plan to review
        injury_history: User's injury history
    
    Returns:
        Complete prompt for the physiotherapist LLM
    """
    
    # Format injury history
    injury_text = "None reported" if not injury_history else "\n".join([
        f"- {inj['injury_type']} on {inj.get('injury_date', 'unknown date')} (Severity: {inj['severity']})"
        + (f"\n  Notes: {inj['notes']}" if inj.get('notes') else "")
        for inj in injury_history
    ])
    
    # Extract exercises for review
    exercises = workout_plan.get('exercises', [])
    exercise_list = "\n".join([
        f"{i+1}. {ex.get('name', 'Unknown')} - {ex.get('sets', '?')} sets x {ex.get('reps', '?')} reps"
        for i, ex in enumerate(exercises)
    ])
    
    prompt = f"""Review the following workout plan for safety concerns based on the user's injury history.

**Injury History:**
{injury_text}

**Proposed Workout Plan:**
Name: {workout_plan.get('name', 'Unknown')}
Frequency: {workout_plan.get('frequency', 'Unknown')}

**Exercises:**
{exercise_list}

**Warm-up:** {workout_plan.get('warm_up', 'Not specified')}
**Cool-down:** {workout_plan.get('cool_down', 'Not specified')}

Your task:
1. Cross-reference each exercise against the injury history
2. Identify any movements that could aggravate existing injuries
3. Consider joint angles, loading patterns, and range of motion
4. Determine if the plan is SAFE or UNSAFE

**Decision Criteria:**
- SAFE: All exercises are compatible with injury history OR user has no injuries
- UNSAFE: ≥1 exercise poses clear risk of re-injury or aggravation

Return ONLY a valid JSON object with this structure (no markdown, no extra text):

{{
    "status": "SAFE" or "UNSAFE",
    "feedback": "Detailed explanation of your assessment. If UNSAFE, specify exactly which exercises are problematic and WHY based on the specific injury.",
    "flagged_exercises": ["Exercise 1", "Exercise 2"]  // Leave empty array if SAFE
}}

Examples:
- Rotator cuff injury → Flag overhead press, military press, upright rows
- ACL tear → Flag deep squats, jumping movements  
- Lower back issues → Flag deadlifts without proper progression, heavy squats

Be specific and cite the injury type in your feedback."""
    
    return prompt
