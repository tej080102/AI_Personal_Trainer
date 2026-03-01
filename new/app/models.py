"""
Database Models for AI Personal Trainer
SQLAlchemy models for PostgreSQL
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User account model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    workouts = relationship("Workout", back_populates="user", cascade="all, delete-orphan")
    injuries = relationship("Injury", back_populates="user", cascade="all, delete-orphan")
    plans = relationship("WorkoutPlan", back_populates="user", cascade="all, delete-orphan")


class Workout(Base):
    """Logged workout entry."""
    __tablename__ = "workouts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    exercise = Column(String(100), nullable=False)
    sets = Column(Integer, nullable=True)
    reps = Column(String(50), nullable=True)  # Can be "10" or "[10,8,6]"
    weight = Column(Float, nullable=True)  # kg
    distance = Column(Float, nullable=True)  # km
    duration = Column(Float, nullable=True)  # minutes
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="workouts")


class Injury(Base):
    """User injury profile."""
    __tablename__ = "injuries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    injury_type = Column(String(100), nullable=False)
    injury_date = Column(DateTime, nullable=False)
    severity = Column(String(20), nullable=False)  # mild, moderate, severe
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)  # Still affecting training?
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="injuries")


class WorkoutPlan(Base):
    """Generated workout plans history."""
    __tablename__ = "workout_plans"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_name = Column(String(200), nullable=False)
    plan_data = Column(JSON, nullable=False)  # Full plan JSON
    critique_data = Column(JSON, nullable=True)  # Safety critique
    revision_count = Column(Integer, default=1)
    safety_status = Column(String(20), nullable=False)  # SAFE or UNSAFE
    goals = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # LLM Metrics
    total_latency_ms = Column(Integer, nullable=True)
    llm_calls = Column(Integer, nullable=True)
    tokens_estimated = Column(Integer, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="plans")


class LLMMetrics(Base):
    """LLM performance metrics log."""
    __tablename__ = "llm_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    endpoint = Column(String(50), nullable=False)
    user_id = Column(Integer, nullable=True)
    
    # Performance metrics
    latency_ms = Column(Integer, nullable=False)
    tokens_input = Column(Integer, nullable=True)
    tokens_output = Column(Integer, nullable=True)
    model_name = Column(String(50), nullable=True)
    
    # Request info
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    revision_count = Column(Integer, nullable=True)
    safety_triggered = Column(Boolean, default=False)
