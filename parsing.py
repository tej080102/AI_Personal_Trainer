import re
import json
import datetime
import pandas as pd

# ---------------- Normalization Helpers ---------------- #
def normalize_date(d):
    """Convert strings like 'today'/'yesterday' to YYYY-MM-DD."""
    if not d:
        return None
    if isinstance(d, datetime.date):
        return str(d)
    s = str(d).strip().lower()
    if s == "today":
        return str(datetime.date.today())
    if s == "yesterday":
        return str(datetime.date.today() - datetime.timedelta(days=1))
    try:
        return str(pd.to_datetime(s).date())
    except Exception:
        return s

def normalize_value(v):
    """Convert common strings/numbers into int/float or None."""
    if v is None:
        return None
    try:
        if isinstance(v, (int, float)):
            return v
        s = str(v).strip().lower()
        if s in ("none", "null", "-", ""):
            return None
        if s.endswith("kg"):
            return float(s.replace("kg", "").strip())
        if s.endswith("lbs") or s.endswith("lb"):
            num = float(s.replace("lbs", "").replace("lb", "").strip())
            return round(num * 0.453592, 1)
        return float(s)
    except Exception:
        return v

# ---------------- Regex Parsing ---------------- #
# For structured fallback if LLM fails
LIFT_RE = re.compile(
    r"(?P<sets>\d+)\s*sets?\s*(?:of\s*)?(?P<reps>\d+)?\s*(?P<exercise>[a-zA-Z ]+)"
    r"(?:\s*(?P<weight>\d+)\s*(kg|lbs))?",
    re.IGNORECASE
)

CARDIO_RE = re.compile(
    r"(?P<distance>[\d\.]+)\s*(km|kilometers|mi|miles)"
    r"(?:\s*(run|jog|cycle|bike|swim|walk))?"
    r"(?:\s*(?:in|for)\s*(?P<duration>[\d\.]+)\s*(min|minutes|hr|hrs|hours))?",
    re.IGNORECASE
)

def regex_parse(text: str):
    """Try to parse workouts from plain text using regex."""
    out = []

    # Lifting matches
    for m in LIFT_RE.finditer(text):
        sets = int(m.group("sets")) if m.group("sets") else None
        reps = int(m.group("reps")) if m.group("reps") else None
        ex = m.group("exercise").strip().lower()
        w = normalize_value(m.group("weight"))
        out.append({
            "date": str(datetime.date.today()),
            "exercise": ex,
            "sets": sets,
            "reps": reps,
            "weight": w,
            "distance": None,
            "duration": None,
            "notes": ""
        })

    # Cardio matches
    for m in CARDIO_RE.finditer(text):
        dist = float(m.group("distance"))
        unit = m.group(2).lower()
        if "mile" in unit:
            dist = dist * 1.60934
        dur = None
        if m.group("duration"):
            dur = float(m.group("duration"))
            if "hr" in m.group(6).lower():
                dur *= 60  # convert hours to minutes
        ex = m.group(3) if m.group(3) else "cardio"
        out.append({
            "date": str(datetime.date.today()),
            "exercise": ex.lower(),
            "sets": None,
            "reps": None,
            "weight": None,
            "distance": round(dist, 2),
            "duration": dur,
            "notes": ""
        })

    return out

# ---------------- JSON Extraction ---------------- #
def extract_json(text: str):
    """Extract JSON from LLM output (strip code fences if needed)."""
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        # Try to extract fenced JSON
        m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                return None
    return None
