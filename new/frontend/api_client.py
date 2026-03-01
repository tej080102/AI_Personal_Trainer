"""
API Client for FastAPI Backend
Handles all HTTP calls to the backend API.
"""

import requests
from typing import Optional, Dict, List
import streamlit as st

class APIClient:
    """HTTP client for AI Personal Trainer API."""
    
    def __init__(self, base_url: str = "http://api:8000"):
        self.base_url = base_url
        self.token: Optional[str] = None
    
    def _headers(self) -> Dict[str, str]:
        """Get headers with auth token."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def _handle_response(self, response: requests.Response) -> Dict:
        """Handle API response."""
        if response.status_code == 401:
            st.session_state["token"] = None
            st.session_state["user"] = None
            raise Exception("Session expired. Please log in again.")
        
        if response.status_code >= 400:
            try:
                error = response.json().get("detail", response.text)
            except:
                error = response.text
            raise Exception(f"API Error: {error}")
        
        return response.json()
    
    # ============= Auth ============= #
    
    def signup(self, username: str, email: str, password: str) -> Dict:
        """Register a new user."""
        response = requests.post(
            f"{self.base_url}/auth/signup",
            json={"username": username, "email": email, "password": password},
            timeout=10
        )
        return self._handle_response(response)
    
    def login(self, username: str, password: str) -> Dict:
        """Login and get JWT token."""
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"username": username, "password": password},
            timeout=10
        )
        result = self._handle_response(response)
        self.token = result.get("access_token")
        return result
    
    def get_me(self) -> Dict:
        """Get current user info."""
        response = requests.get(
            f"{self.base_url}/auth/me",
            headers=self._headers(),
            timeout=10
        )
        return self._handle_response(response)
    
    # ============= Workouts ============= #
    
    def get_workouts(self, limit: int = 100) -> List[Dict]:
        """Get user's workout history."""
        response = requests.get(
            f"{self.base_url}/workouts?limit={limit}",
            headers=self._headers(),
            timeout=10
        )
        return self._handle_response(response)
    
    def create_workout(self, workout: Dict) -> Dict:
        """Create a new workout entry."""
        response = requests.post(
            f"{self.base_url}/workouts",
            json=workout,
            headers=self._headers(),
            timeout=10
        )
        return self._handle_response(response)
    
    def create_workouts_batch(self, workouts: List[Dict]) -> List[Dict]:
        """Create multiple workout entries."""
        response = requests.post(
            f"{self.base_url}/workouts/batch",
            json=workouts,
            headers=self._headers(),
            timeout=10
        )
        return self._handle_response(response)
    
    def get_workout_stats(self) -> Dict:
        """Get workout statistics for dashboard."""
        response = requests.get(
            f"{self.base_url}/workouts/stats",
            headers=self._headers(),
            timeout=10
        )
        return self._handle_response(response)
    
    def delete_workout(self, workout_id: int) -> None:
        """Delete a workout entry."""
        response = requests.delete(
            f"{self.base_url}/workouts/{workout_id}",
            headers=self._headers(),
            timeout=10
        )
        if response.status_code >= 400:
            raise Exception("Failed to delete workout")
    
    def clear_workouts(self, exercise: Optional[str] = None) -> None:
        """Clear workouts."""
        url = f"{self.base_url}/workouts"
        if exercise:
            url += f"?exercise={exercise}"
        response = requests.delete(url, headers=self._headers(), timeout=10)
        if response.status_code >= 400:
            raise Exception("Failed to clear workouts")
    
    # ============= Injuries ============= #
    
    def get_injuries(self, active_only: bool = False) -> List[Dict]:
        """Get user's injury profile."""
        response = requests.get(
            f"{self.base_url}/injuries?active_only={str(active_only).lower()}",
            headers=self._headers(),
            timeout=10
        )
        return self._handle_response(response)
    
    def create_injury(self, injury: Dict) -> Dict:
        """Add a new injury."""
        response = requests.post(
            f"{self.base_url}/injuries",
            json=injury,
            headers=self._headers(),
            timeout=10
        )
        return self._handle_response(response)
    
    def update_injury(self, injury_id: int, injury: Dict) -> Dict:
        """Update an injury."""
        response = requests.patch(
            f"{self.base_url}/injuries/{injury_id}",
            json=injury,
            headers=self._headers(),
            timeout=10
        )
        return self._handle_response(response)
    
    def delete_injury(self, injury_id: int) -> None:
        """Delete an injury."""
        response = requests.delete(
            f"{self.base_url}/injuries/{injury_id}",
            headers=self._headers(),
            timeout=10
        )
        if response.status_code >= 400:
            raise Exception("Failed to delete injury")
    
    # ============= Plans ============= #
    
    def get_plans(self, limit: int = 50) -> List[Dict]:
        """Get saved workout plans."""
        response = requests.get(
            f"{self.base_url}/plans?limit={limit}",
            headers=self._headers(),
            timeout=10
        )
        return self._handle_response(response)
    
    def get_plan(self, plan_id: int) -> Dict:
        """Get a specific plan."""
        response = requests.get(
            f"{self.base_url}/plans/{plan_id}",
            headers=self._headers(),
            timeout=10
        )
        return self._handle_response(response)
    
    def save_plan(self, plan: Dict) -> Dict:
        """Save a generated plan."""
        response = requests.post(
            f"{self.base_url}/plans",
            json=plan,
            headers=self._headers(),
            timeout=10
        )
        return self._handle_response(response)
    
    def delete_plan(self, plan_id: int) -> None:
        """Delete a plan."""
        response = requests.delete(
            f"{self.base_url}/plans/{plan_id}",
            headers=self._headers(),
            timeout=10
        )
        if response.status_code >= 400:
            raise Exception("Failed to delete plan")
    
    def get_plan_stats(self) -> Dict:
        """Get plan statistics."""
        response = requests.get(
            f"{self.base_url}/plans/stats/summary",
            headers=self._headers(),
            timeout=10
        )
        return self._handle_response(response)
    
    # ============= AI Coach (LangGraph) ============= #
    
    def generate_plan(self, user_profile: Dict, injury_history: List[Dict], thread_id: str) -> Dict:
        """Generate a workout plan using LangGraph."""
        response = requests.post(
            f"{self.base_url}/plan",
            json={
                "user_profile": user_profile,
                "injury_history": injury_history,
                "thread_id": thread_id
            },
            headers=self._headers(),
            timeout=300  # 5 minute timeout for LLM
        )
        return self._handle_response(response)
    
    # ============= Metrics ============= #
    
    def get_llm_metrics_summary(self) -> Dict:
        """Get LLM performance summary."""
        response = requests.get(
            f"{self.base_url}/metrics/llm/summary",
            headers=self._headers(),
            timeout=10
        )
        return self._handle_response(response)
    
    # ============= Health ============= #
    
    def health_check(self) -> Dict:
        """Check API health."""
        response = requests.get(f"{self.base_url}/health", timeout=5)
        return self._handle_response(response)
