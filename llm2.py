# llm2.py
import os
import re
import json
import streamlit as st
from typing import Dict, Optional
from huggingface_hub import InferenceClient

DEFAULT_MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"
MODEL_ID = os.getenv("HF_MODEL_ID", DEFAULT_MODEL_ID).strip()


def get_huggingface_api_key() -> Optional[str]:
    for k in ("HUGGINGFACE_API_KEY", "HF_API_KEY", "hf_api_key"):
        try:
            if k in st.secrets and st.secrets[k]:
                return str(st.secrets[k]).strip()
        except Exception:
            pass
        if os.getenv(k):
            return os.getenv(k).strip()
        if st.session_state.get(k):
            return str(st.session_state[k]).strip()
    return None


def setup_api_key_ui():
    api_key = get_huggingface_api_key()
    if not api_key:
        st.warning("⚠️ Hugging Face API key not found.")
        entered = st.text_input(
            "Enter your Hugging Face API key:",
            type="password",
            help="Get your key at https://huggingface.co/settings/tokens",
        )
        if entered:
            st.session_state["HUGGINGFACE_API_KEY"] = entered.strip()
            st.success("✅ API key saved for this session.")
            return entered.strip()
        return None
    return api_key


def call_huggingface(prompt: str, max_tokens: int = 400) -> Dict[str, str]:
    """
    Call Llama 3.1 8B Instruct via chat_completion API.
    Always return a dict with {ok, output, error}.
    """
    api_key = get_huggingface_api_key()
    if not api_key:
        return {"ok": False, "output": "", "error": "Missing Hugging Face API key."}

    try:
        client = InferenceClient(model=MODEL_ID, token=api_key)

        resp = client.chat_completion(
            model=MODEL_ID,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.1,
        )

        output = resp["choices"][0]["message"]["content"]

        # Try to clean/extract JSON if the model wrapped it in code fences
        try:
            json.loads(output)
            clean = output
        except json.JSONDecodeError:
            m = re.search(r"```(?:json)?\s*(.*?)```", output, re.DOTALL)
            clean = m.group(1).strip() if m else output

        return {"ok": True, "output": clean, "error": ""}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ok": False, "output": "", "error": f"Inference error: {repr(e)}"}

