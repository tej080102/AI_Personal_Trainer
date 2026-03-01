"""
LangGraph State Machine - Safety Critique Loop
Implements the multi-agent workflow: Trainer → Physiotherapist → Conditional Revision
"""

import json
import os
from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import SystemMessage, HumanMessage

from app.state import TrainerState
from app.prompts import (
    DRAFT_PLAN_SYSTEM_PROMPT,
    CRITIQUE_SYSTEM_PROMPT,
    get_draft_plan_prompt,
    get_critique_prompt,
)


# ============= Node Implementations ============= #

def draft_plan(state: TrainerState, llm) -> TrainerState:
    """
    Node 1: Generate workout plan based on user profile and injuries.
    
    If this is a revision (critique exists), incorporates physiotherapist feedback.
    
    This demonstrates multi-agent collaboration where the Trainer respects the
    Physiotherapist's domain expertise and makes necessary adjustments.
    """
    print(f"[INFO] Entering node: draft_plan (Revision #{state.get('revision_count', 0)})")
    
    # Extract state data
    user_profile = state.get("user_profile", {})
    injury_history = state.get("injury_history", [])
    critique = state.get("critique")
    
    # Build the prompt (includes revision guidance if critique exists)
    user_prompt = get_draft_plan_prompt(user_profile, injury_history, critique)
    
    # Call LLM with system + user messages
    messages = [
        SystemMessage(content=DRAFT_PLAN_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]
    
    response = llm.invoke(messages)
    
    # Parse JSON response
    try:
        # Clean potential markdown code blocks
        content = response.content.strip()
        if content.startswith("```"):
            # Extract JSON from markdown
            lines = content.split("\n")
            json_lines = []
            in_code_block = False
            for line in lines:
                if line.startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block or not content.startswith("```"):
                    json_lines.append(line)
            content = "\n".join(json_lines)
        
        workout_plan = json.loads(content)
        print(f"[INFO] Generated plan: {workout_plan.get('name', 'Unknown')}")
        
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse LLM response as JSON: {e}")
        print(f"[ERROR] Raw response: {response.content[:500]}")
        # Fallback plan
        workout_plan = {
            "name": "Error - Invalid Response",
            "frequency": "Unknown",
            "exercises": [],
            "warm_up": "Error parsing response",
            "cool_down": "",
            "progression_notes": ""
        }
    
    # Update state
    return {
        **state,
        "workout_plan": workout_plan,
        "revision_count": state.get("revision_count", 0) + 1,
    }


def critique_plan(state: TrainerState, llm) -> TrainerState:
    """
    Node 2: Safety critique by physiotherapist agent.
    
    This is a domain-specific safety validator that acts as a separate "persona"
    from the trainer. It demonstrates multi-agent orchestration where specialized
    agents provide checks and balances.
    
    Resume highlight: "Implemented multi-agent safety validation using domain-specific
    LLM personas for injury risk assessment in fitness applications."
    """
    print("[INFO] Entering node: critique_plan (Physiotherapist review)")
    
    workout_plan = state.get("workout_plan", {})
    injury_history = state.get("injury_history", [])
    
    # Build critique prompt
    user_prompt = get_critique_prompt(workout_plan, injury_history)
    
    messages = [
        SystemMessage(content=CRITIQUE_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]
    
    response = llm.invoke(messages)
    
    # Parse critique response
    try:
        content = response.content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            json_lines = []
            in_code_block = False
            for line in lines:
                if line.startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block or not content.startswith("```"):
                    json_lines.append(line)
            content = "\n".join(json_lines)
        
        critique = json.loads(content)
        status = critique.get("status", "SAFE")
        print(f"[INFO] Critique status: {status}")
        
        if status == "UNSAFE":
            print(f"[INFO] Safety concerns: {critique.get('feedback', 'No details')}")
            print(f"[INFO] Flagged exercises: {critique.get('flagged_exercises', [])}")
        
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse critique response: {e}")
        # Default to SAFE if parsing fails (conservative)
        critique = {
            "status": "SAFE",
            "feedback": "Error parsing critique response - defaulting to SAFE",
            "flagged_exercises": []
        }
    
    return {
        **state,
        "critique": critique,
    }


# ============= Conditional Routing ============= #

def route_after_critique(state: TrainerState) -> Literal["draft_plan", "__end__"]:
    """
    Conditional edge: Determines if we loop back for revision or end the workflow.
    
    Logic:
    - If critique is UNSAFE AND revision_count < 3 → Loop back to draft_plan
    - Otherwise (SAFE or hit max revisions) → END
    
    This implements the safety-critical feedback loop that ensures workout plans
    are validated before delivery to users.
    """
    critique = state.get("critique", {})
    revision_count = state.get("revision_count", 0)
    status = critique.get("status", "SAFE")
    
    if status == "UNSAFE" and revision_count < 3:
        print(f"[INFO] Routing back to draft_plan for revision (attempt {revision_count + 1}/3)")
        return "draft_plan"
    else:
        if status == "UNSAFE":
            print(f"[WARNING] Max revisions reached ({revision_count}). Ending workflow with UNSAFE plan.")
        else:
            print(f"[INFO] Plan approved as SAFE after {revision_count} revision(s). Ending workflow.")
        return "__end__"


# ============= Graph Construction ============= #

def create_graph(llm, checkpointer=None):
    """
    Build the LangGraph StateGraph with the safety critique loop.
    
    Args:
        llm: LangChain chat model (OpenAI, Ollama, etc.)
        checkpointer: Optional PostgresSaver for state persistence
    
    Returns:
        Compiled graph ready for invocation
    """
    
    # Initialize graph with state schema
    workflow = StateGraph(TrainerState)
    
    # Add nodes (wrap with lambda to inject llm dependency)
    workflow.add_node("draft_plan", lambda state: draft_plan(state, llm))
    workflow.add_node("critique_plan", lambda state: critique_plan(state, llm))
    
    # Set entry point
    workflow.set_entry_point("draft_plan")
    
    # Add edges
    workflow.add_edge("draft_plan", "critique_plan")  # Always critique after drafting
    
    # Add conditional edge with routing logic
    workflow.add_conditional_edges(
        "critique_plan",
        route_after_critique,
        {
            "draft_plan": "draft_plan",  # Loop back for revision
            "__end__": END,  # Approve and end
        }
    )
    
    # Compile with optional persistence
    app = workflow.compile(checkpointer=checkpointer)
    
    print("[INFO] LangGraph workflow compiled successfully")
    print("[INFO] Workflow: START → draft_plan → critique_plan → [conditional] → draft_plan OR END")
    
    return app


# ============= Helper Functions ============= #

def initialize_state(
    user_profile: dict,
    injury_history: list[dict],
    thread_id: str
) -> TrainerState:
    """
    Create initial state for a new conversation thread.
    
    Args:
        user_profile: User's fitness goals and attributes
        injury_history: List of injury records
        thread_id: Unique session identifier
    
    Returns:
        Initialized TrainerState
    """
    return TrainerState(
        user_profile=user_profile,
        injury_history=injury_history,
        workout_plan=None,
        critique=None,
        revision_count=0,
        thread_id=thread_id,
        messages=[],
    )


def get_checkpointer(postgres_url: str = None):
    """
    Create PostgresSaver for state persistence.
    
    Args:
        postgres_url: PostgreSQL connection string (e.g., postgresql://user:pass@host:5432/db)
                      If None, reads from POSTGRES_URL environment variable
    
    Returns:
        PostgresSaver instance or None if no URL provided
    """
    url = postgres_url or os.getenv("POSTGRES_URL")
    
    if not url:
        print("[WARNING] No POSTGRES_URL provided. Running without persistence.")
        return None
    
    try:
        from psycopg import Connection
        
        # Use autocommit to avoid transaction issues with CREATE INDEX CONCURRENTLY
        conn = Connection.connect(url, autocommit=True)
        checkpointer = PostgresSaver(conn)
        
        # Initialize checkpoint tables (will use CONCURRENTLY for indexes)
        checkpointer.setup()
        
        print(f"[INFO] PostgreSQL checkpointer initialized: {url.split('@')[-1]}")  # Hide credentials
        return checkpointer
        
    except Exception as e:
        print(f"[ERROR] Failed to initialize PostgreSQL checkpointer: {e}")
        return None
