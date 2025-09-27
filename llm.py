import subprocess
import streamlit as st

MODEL_NAME = "mistral"

def call_ollama(prompt: str, timeout: int = 30) -> dict:
    """Send a prompt to Ollama model and return dict {ok, stdout, stderr}.
    If the model is missing, automatically pull it once and retry.
    """
    def run_model():
        return subprocess.run(
            ["ollama", "run",  MODEL_NAME],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    try:
        proc = run_model()
        if proc.returncode != 0 and "not found" in (proc.stderr or "").lower():
            st.info(f"📥 Pulling model '{MODEL_NAME}' (this may take a while on first run)...")
            pull = subprocess.run(
                ["ollama", "pull", MODEL_NAME],
                capture_output=True,
                text=True,
                timeout=None,
            )
            if pull.returncode == 0:
                proc = run_model()
            else:
                return {"ok": False, "stdout": "", "stderr": pull.stderr or "Model pull failed."}
        return {
            "ok": proc.returncode == 0,
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
        }
    except FileNotFoundError:
        return {"ok": False, "stdout": "", "stderr": "Ollama not found. Install or add to PATH."}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "Ollama run timed out."}
