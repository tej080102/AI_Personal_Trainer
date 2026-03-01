"""
LangGraph State Schema
Defines the TrainerState TypedDict for the state graph.
"""

from typing import TypedDict, Optional


class TrainerState(TypedDict, total=False):
    """
    State schema for the Personal Trainer Agent.
    
    The state flows through the graph nodes and maintains conversation context.
    Persisted to PostgreSQL via LangGraph's PostgresSaver.
    """
    
    # User input data
    user_profile: dict  # {goals: str, fitness_level: str, weight: float, etc.}
    injury_history: list[dict]  # [{injury_type, date, severity, notes}, ...]
    
    # Generated outputs
    workout_plan: Optional[dict]  # The drafted workout plan
    critique: Optional[dict]  # {status: "SAFE"|"UNSAFE", feedback: str}
    
    # Loop control
    revision_count: int  # Number of revisions made (max 3)
    
    # Session management
    thread_id: str  # User session identifier for persistence
    
    # Conversation context
    messages: list[dict]  # Chat history for LLM context
