"""
FastAPI Server - Enhanced Version with Auth, Workouts, and LLM Metrics
Production-grade REST API for AI Personal Trainer using local LLM.
"""

import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.chat_models import ChatOllama
import logging

from app.schemas import (
    WorkoutRequest,
    PlanResponse,
    HistoryResponse,
    HealthResponse,
    WorkoutPlan,
    Critique,
)
from app.graph import create_graph, initialize_state, get_checkpointer
from app.database import init_database, SessionLocal
from app.models import LLMMetrics

# Import routers
from app.routers import auth, workouts, injuries, plans

# ============= Configuration ============= #

# Logging setup with LLM metrics
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create a special logger for LLM metrics
llm_metrics_logger = logging.getLogger("llm_metrics")
llm_metrics_logger.setLevel(logging.INFO)

# Environment variables
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
POSTGRES_URL = os.getenv("POSTGRES_URL")

# Global state
graph_app = None
checkpointer = None


# ============= LLM Metrics Logging ============= #

def log_llm_metrics(
    endpoint: str,
    latency_ms: int,
    success: bool = True,
    error_message: str = None,
    revision_count: int = None,
    safety_triggered: bool = False,
    tokens_input: int = None,
    tokens_output: int = None,
    user_id: int = None
):
    """Log LLM request metrics to both logger and database."""
    
    # Log to console with styled output
    status_icon = "✅" if success else "❌"
    latency_color = "🟢" if latency_ms < 5000 else "🟡" if latency_ms < 15000 else "🔴"
    
    llm_metrics_logger.info(
        f"{status_icon} LLM Request Complete | "
        f"Endpoint: {endpoint} | "
        f"Latency: {latency_color} {latency_ms}ms | "
        f"Revisions: {revision_count or 0} | "
        f"Safety Triggered: {'Yes' if safety_triggered else 'No'}"
    )
    
    # Log detailed metrics
    if tokens_input or tokens_output:
        llm_metrics_logger.info(
            f"   📊 Tokens: Input={tokens_input or 'N/A'}, Output={tokens_output or 'N/A'}"
        )
    
    # Save to database
    try:
        db = SessionLocal()
        metric = LLMMetrics(
            endpoint=endpoint,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            revision_count=revision_count,
            safety_triggered=safety_triggered,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            user_id=user_id,
            model_name=OLLAMA_MODEL
        )
        db.add(metric)
        db.commit()
        db.close()
    except Exception as e:
        logger.warning(f"Failed to save LLM metrics to database: {e}")


# ============= Lifespan Management ============= #

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize LLM, database, and graph on startup, cleanup on shutdown."""
    global graph_app, checkpointer
    
    try:
        # Initialize SQLAlchemy database tables
        logger.info("Initializing database tables...")
        init_database()
        
        logger.info(f"Initializing Ollama LLM: {OLLAMA_MODEL} @ {OLLAMA_BASE_URL}")
        
        # Initialize LLM
        llm = ChatOllama(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_MODEL,
            temperature=0.7,
        )
        
        # Test LLM connectivity with metrics
        start_time = time.time()
        try:
            # Simple test with timeout control if possible, or just catch error
            # Note: invoke is blocking, so this delays startup
            test_response = llm.invoke("Say 'OK' if you're ready")
            latency_ms = int((time.time() - start_time) * 1000)
            logger.info(f"LLM test successful: {test_response.content[:50]}")
            log_llm_metrics("startup_test", latency_ms, success=True)
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"LLM test failed (continuing anyway): {e}")
            log_llm_metrics("startup_test", latency_ms, success=False, error_message=str(e))
            # Do NOT raise, so API can start even if LLM is waking up
            # raise
        
        # Initialize checkpointer
        if POSTGRES_URL:
            checkpointer = get_checkpointer(POSTGRES_URL)
        else:
            logger.warning("No POSTGRES_URL set. Running without state persistence.")
        
        # Create graph
        graph_app = create_graph(llm, checkpointer)
        logger.info("FastAPI server initialized successfully (Local Ollama mode)")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize server: {e}")
        raise
    finally:
        logger.info("Shutting down server...")
        if checkpointer:
            try:
                checkpointer.conn.close()
            except:
                pass


# ============= FastAPI App ============= #

app = FastAPI(
    title="AI Personal Trainer API",
    description="Agentic workout planning with LangGraph safety critique loop, user authentication, and workout tracking",
    version="2.1.0",
    lifespan=lifespan,
)

# CORS middleware for web clients
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8501,http://frontend:8501").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(workouts.router)
app.include_router(injuries.router)
app.include_router(plans.router)


# ============= Request Timing Middleware ============= #

@app.middleware("http")
async def add_request_timing(request: Request, call_next):
    """Add timing header to all responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time-Ms"] = str(int(process_time * 1000))
    return response


# ============= Endpoints ============= #

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        HealthResponse with service status
    """
    database_status = "connected" if checkpointer else "disconnected"
    overall_status = "healthy" if graph_app and database_status == "connected" else "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        database=database_status,
        llm_provider=f"Ollama ({OLLAMA_MODEL})"
    )


@app.get("/metrics/llm", tags=["Metrics"])
async def get_llm_metrics(limit: int = 100):
    """
    Get recent LLM performance metrics.
    
    Returns:
        List of recent LLM request metrics
    """
    try:
        db = SessionLocal()
        metrics = db.query(LLMMetrics).order_by(LLMMetrics.timestamp.desc()).limit(limit).all()
        db.close()
        
        return {
            "total": len(metrics),
            "metrics": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "endpoint": m.endpoint,
                    "latency_ms": m.latency_ms,
                    "success": m.success,
                    "revision_count": m.revision_count,
                    "safety_triggered": m.safety_triggered,
                    "model": m.model_name
                }
                for m in metrics
            ]
        }
    except Exception as e:
        logger.error(f"Failed to fetch LLM metrics: {e}")
        return {"total": 0, "metrics": [], "error": str(e)}


@app.get("/metrics/llm/summary", tags=["Metrics"])
async def get_llm_metrics_summary():
    """
    Get LLM performance summary statistics.
    
    Returns:
        Summary of LLM performance (avg latency, success rate, etc.)
    """
    from sqlalchemy import func
    
    try:
        db = SessionLocal()
        
        total = db.query(LLMMetrics).count()
        successful = db.query(LLMMetrics).filter(LLMMetrics.success == True).count()
        avg_latency = db.query(func.avg(LLMMetrics.latency_ms)).scalar() or 0
        min_latency = db.query(func.min(LLMMetrics.latency_ms)).scalar() or 0
        max_latency = db.query(func.max(LLMMetrics.latency_ms)).scalar() or 0
        safety_triggers = db.query(LLMMetrics).filter(LLMMetrics.safety_triggered == True).count()
        
        db.close()
        
        return {
            "total_requests": total,
            "successful_requests": successful,
            "success_rate": round(successful / total * 100, 2) if total > 0 else 0,
            "avg_latency_ms": int(avg_latency),
            "min_latency_ms": min_latency,
            "max_latency_ms": max_latency,
            "safety_triggers": safety_triggers,
            "model": OLLAMA_MODEL
        }
    except Exception as e:
        logger.error(f"Failed to fetch LLM metrics summary: {e}")
        return {"error": str(e)}


@app.post("/plan", response_model=PlanResponse, tags=["Workout Planning"])
async def generate_plan(request: WorkoutRequest):
    """
    Generate a workout plan with safety critique loop.
    
    Flow:
    1. Initialize state with user profile and injury history
    2. Invoke LangGraph workflow (draft → critique → conditional revision)
    3. Return final plan + critique
    
    Args:
        request: WorkoutRequest with user profile, injuries, and thread_id
    
    Returns:
        PlanResponse with workout plan and safety assessment
    
    Raises:
        HTTPException: 500 if graph execution fails
    """
    if not graph_app:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Graph not initialized. Check server logs."
        )
    
    start_time = time.time()
    
    try:
        logger.info(f"Generating plan for thread_id={request.thread_id}")
        
        # Initialize state
        initial_state = initialize_state(
            user_profile=request.user_profile.model_dump(),
            injury_history=[inj.model_dump() for inj in request.injury_history],
            thread_id=request.thread_id,
        )
        
        # Configure thread persistence
        config = {
            "configurable": {
                "thread_id": request.thread_id
            }
        }
        
        # Invoke graph workflow
        final_state = graph_app.invoke(initial_state, config=config)
        
        # Calculate metrics
        latency_ms = int((time.time() - start_time) * 1000)
        revision_count = final_state.get('revision_count', 0)
        safety_triggered = revision_count > 1
        
        # Estimate tokens (rough approximation)
        import json
        output_str = json.dumps(final_state.get("workout_plan", {})) + json.dumps(final_state.get("critique", {}))
        tokens_estimated = len(output_str) // 4
        
        # Log LLM metrics
        log_llm_metrics(
            endpoint="/plan",
            latency_ms=latency_ms,
            success=True,
            revision_count=revision_count,
            safety_triggered=safety_triggered,
            tokens_output=tokens_estimated
        )
        
        logger.info(f"Plan generated successfully. Revisions: {revision_count}, Latency: {latency_ms}ms")
        
        # Parse response
        workout_plan = WorkoutPlan(**final_state["workout_plan"])
        critique = Critique(**final_state["critique"])
        
        return PlanResponse(
            workout_plan=workout_plan,
            critique=critique,
            revision_count=revision_count,
            thread_id=request.thread_id,
        )
        
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        log_llm_metrics(
            endpoint="/plan",
            latency_ms=latency_ms,
            success=False,
            error_message=str(e)
        )
        
        logger.error(f"Error generating plan: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate plan: {str(e)}"
        )


@app.get("/history/{thread_id}", response_model=HistoryResponse, tags=["History"])
async def get_history(thread_id: str):
    """
    Retrieve conversation history for a thread.
    
    Args:
        thread_id: Session identifier
    
    Returns:
        HistoryResponse with list of previous states
    
    Raises:
        HTTPException: 404 if thread not found, 503 if no persistence configured
    """
    if not checkpointer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence not configured. Set POSTGRES_URL to enable history."
        )
    
    try:
        logger.info(f"Fetching history for thread_id={thread_id}")
        
        # Query checkpoints from database
        config = {"configurable": {"thread_id": thread_id}}
        
        # Get state history from checkpointer
        history_items = []
        
        # Try to get the latest state
        try:
            state = graph_app.get_state(config)
            if state and state.values:
                from datetime import datetime
                
                # Extract workout plan safely (may be raw dict from LLM)
                raw_plan = state.values.get("workout_plan")
                raw_critique = state.values.get("critique")
                
                history_items.append({
                    "timestamp": datetime.now().isoformat(),
                    "workout_plan": raw_plan if isinstance(raw_plan, dict) else None,
                    "critique": raw_critique if isinstance(raw_critique, dict) else None,
                    "revision_count": state.values.get("revision_count", 0),
                })
        except Exception as state_err:
            logger.warning(f"Could not retrieve state for {thread_id}: {state_err}")
        
        if not history_items:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No history found for thread_id={thread_id}"
            )
        
        return HistoryResponse(
            thread_id=thread_id,
            history=history_items
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch history: {str(e)}"
        )


# ============= Server Entry Point ============= #

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Disable in production
        log_level="info"
    )
