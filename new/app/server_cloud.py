"""
FastAPI Server - Cloud Mode (OpenAI)
Production-grade REST API for AI Personal Trainer using OpenAI GPT-4o.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI
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

# ============= Configuration ============= #

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
POSTGRES_URL = os.getenv("POSTGRES_URL")

# Global state
graph_app = None
checkpointer = None


# ============= Lifespan Management ============= #

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize LLM and graph on startup, cleanup on shutdown."""
    global graph_app, checkpointer
    
    try:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        logger.info(f"Initializing OpenAI LLM: {OPENAI_MODEL}")
        
        # Initialize LLM
        llm = ChatOpenAI(
            model=OPENAI_MODEL,
            temperature=0.7,
            api_key=OPENAI_API_KEY,
        )
        
        # Test LLM connectivity
        try:
            test_response = llm.invoke("Say 'OK' if you're ready")
            logger.info(f"LLM test successful: {test_response.content[:50]}")
        except Exception as e:
            logger.error(f"LLM test failed: {e}")
            raise
        
        # Initialize checkpointer
        if POSTGRES_URL:
            checkpointer = get_checkpointer(POSTGRES_URL)
        else:
            logger.warning("No POSTGRES_URL set. Running without state persistence.")
        
        # Create graph
        graph_app = create_graph(llm, checkpointer)
        logger.info("FastAPI server initialized successfully (OpenAI GPT-4o mode)")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize server: {e}")
        raise
    finally:
        logger.info("Shutting down server...")
        if checkpointer:
            # Close database connection
            try:
                checkpointer.conn.close()
            except:
                pass


# ============= FastAPI App ============= #

app = FastAPI(
    title="AI Personal Trainer API (OpenAI)",
    description="Agentic workout planning with LangGraph safety critique loop - Cloud Edition",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        llm_provider=f"OpenAI ({OPENAI_MODEL})"
    )


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
        
        logger.info(f"Plan generated successfully. Revisions: {final_state.get('revision_count', 0)}")
        
        # Parse response
        workout_plan = WorkoutPlan(**final_state["workout_plan"])
        critique = Critique(**final_state["critique"])
        
        return PlanResponse(
            workout_plan=workout_plan,
            critique=critique,
            revision_count=final_state.get("revision_count", 0),
            thread_id=request.thread_id,
        )
        
    except Exception as e:
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
        # Note: This is a simplified version - in production you'd query the checkpoint table directly
        history_items = []
        
        # Try to get the latest state
        try:
            state = graph_app.get_state(config)
            if state and state.values:
                from datetime import datetime
                history_items.append({
                    "timestamp": datetime.now().isoformat(),
                    "workout_plan": state.values.get("workout_plan"),
                    "critique": state.values.get("critique"),
                    "revision_count": state.values.get("revision_count", 0),
                })
        except:
            pass
        
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
        "app.server_cloud:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Disable in production
        log_level="info"
    )
