import requests
import json
import streamlit as st
from typing import Dict, Optional

# The model we'll use from Hugging Face
MODEL_ID = "google/flan-t5-large"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"

def get_huggingface_api_key() -> Optional[str]:
    """Get the Hugging Face API key from Streamlit secrets or environment."""
    # First try to get from Streamlit secrets
    try:
        return st.secrets["HUGGINGFACE_API_KEY"]
    except Exception:
        # Then try to get from session state (if user provided it in UI)
        return st.session_state.get("HUGGINGFACE_API_KEY")

def setup_api_key_ui():
    """Display UI for API key input if not already configured."""
    api_key = get_huggingface_api_key()
    if api_key is None:
        st.warning("⚠️ Hugging Face API key not found in configuration.")
        api_key = st.text_input(
            "Enter your Hugging Face API key:",
            type="password",
            help="Get your API key from https://huggingface.co/settings/tokens"
        )
        if api_key:
            st.session_state["HUGGINGFACE_API_KEY"] = api_key
            st.success("✅ API key saved for this session!")
        return api_key
    return api_key

def call_huggingface(prompt: str, timeout: int = 30) -> Dict[str, str]:
    """Send a prompt to Hugging Face model and return dict {ok, output, error}."""
    api_key = get_huggingface_api_key()
    
    if not api_key:
        return {
            "ok": False,
            "output": "",
            "error": "Hugging Face API key not configured. Please add it in the settings."
        }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        # T5 works better with structured, concise prompts
        if "Role: Expert fitness coach" in prompt:
            # For coaching prompts, keep the structure but make it more concise
            formatted_prompt = prompt
        else:
            # For workout parsing, we already have a concise prompt from app2.py
            formatted_prompt = prompt
        
        response = requests.post(
            API_URL,
            headers=headers,
            json={"inputs": formatted_prompt, "parameters": {"max_length": 512}},
            timeout=timeout
        )

        if response.status_code != 200:
            return {
                "ok": False,
                "output": "",
                "error": f"API Error: {response.text}"
            }

        # Parse and clean the response
        output = response.json()[0]["generated_text"]
        
        # Try to extract JSON if it's wrapped in markdown code blocks
        try:
            # First try to parse as-is
            json.loads(output)
            clean_output = output
        except json.JSONDecodeError:
            # Try to extract from markdown code blocks if present
            import re
            json_match = re.search(r'```(?:json)?\s*(.*?)```', output, re.DOTALL)
            clean_output = json_match.group(1) if json_match else output

        return {
            "ok": True,
            "output": clean_output,
            "error": ""
        }

    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "output": "",
            "error": "Request timed out. Please try again."
        }
    except requests.exceptions.RequestException as e:
        return {
            "ok": False,
            "output": "",
            "error": f"Request failed: {str(e)}"
        }
    except Exception as e:
        return {
            "ok": False,
            "output": "",
            "error": f"Unexpected error: {str(e)}"
        }