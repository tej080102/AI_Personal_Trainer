import subprocess
import json

MODEL_NAME = "mistral"

def call_local_llm(prompt: str, timeout: int = 60, max_tokens: int = 512):
    """
    Call Ollama locally with the mistral model.
    Returns dict {ok, output, error}.
    """
    try:
        # Run ollama command
        result = subprocess.run(
            ["ollama", "run", MODEL_NAME],
            input=prompt.encode("utf-8"),
            capture_output=True,
            timeout=timeout
        )

        if result.returncode != 0:
            return {
                "ok": False,
                "output": "",
                "error": result.stderr.decode("utf-8") if result.stderr else "Unknown Ollama error"
            }

        output = result.stdout.decode("utf-8").strip()

        # Clean JSON if wrapped in markdown
        try:
            json.loads(output)
            clean_output = output
        except Exception:
            import re
            match = re.search(r'```(?:json)?\s*(.*?)```', output, re.DOTALL)
            clean_output = match.group(1).strip() if match else output

        return {"ok": True, "output": clean_output, "error": ""}

    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "", "error": "Request timed out."}
    except Exception as e:
        return {"ok": False, "output": "", "error": str(e)}
