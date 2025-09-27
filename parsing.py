import re, json
from datetime import date, timedelta
from typing import Any, List, Optional, Union

def normalize_date(d: Optional[str]) -> Optional[str]:
    if not d:
        return None
    d = str(d).strip().lower()
    if d == "today":
        return date.today().isoformat()
    elif d == "yesterday":
        return (date.today() - timedelta(days=1)).isoformat()
    else:
        return d

def _parse_list_from_str(v: str):
    parts = re.split(r"[,\s;]+", v.strip())
    out = []
    for p in parts:
        if p.isdigit():
            out.append(int(p))
        else:
            m = re.fullmatch(r"-?\d+", p)
            if m:
                out.append(int(m.group(0)))
    return out or None

def normalize_value(v: Any, as_float: bool = False) -> Optional[Union[int, float, List[int]]]:
    if v is None:
        return None
    if isinstance(v, list):
        out = []
        for item in v:
            try:
                out.append(int(item) if not as_float else float(item))
            except Exception:
                continue
        return out if out else None
    if isinstance(v, (int, float)):
        return float(v) if as_float else int(round(float(v)))
    if isinstance(v, str):
        v = v.strip()
        if any(sep in v for sep in [",", ";", " "]):
            maybe_list = _parse_list_from_str(v)
            if maybe_list:
                return maybe_list
        m = re.search(r"-?\d+(\.\d+)?", v)
        if m:
            num = float(m.group(0))
            return num if as_float else int(round(num))
        return None
    return None

EX_SPLIT_RE = re.compile(r"\s*(?:,| and )\s*", re.I)

def parse_piece(piece: str) -> Optional[dict]:
    p = piece.strip()
    weight = None
    wm = re.search(r"@?\s*(\d+(?:\.\d+)?)\s*(kg|kgs|kilograms|lb|lbs|pounds)?\b", p, re.I)
    if wm:
        weight_num = float(wm.group(1))
        unit = wm.group(2).lower() if wm.group(2) else None
        if unit in ("lb", "lbs", "pounds"):
            weight = round(weight_num * 0.453592, 1)
        else:
            weight = weight_num

    sxr = re.search(r"(\d+)\s*[x×]\s*(\d+)", p, re.I)
    sets = reps = None
    if sxr:
        sets = int(sxr.group(1)); reps = int(sxr.group(2))
    else:
        s_m = re.search(r"(\d+)\s*sets?", p, re.I)
        r_m = re.search(r"(\d+)\s*reps?", p, re.I)
        if s_m: sets = int(s_m.group(1))
        if r_m: reps = int(r_m.group(1))

    cleaned = re.sub(r"@?\s*\d+(?:\.\d+)?\s*(kg|kgs|kilograms|lb|lbs|pounds)\b", " ", p, flags=re.I)
    cleaned = re.sub(r"\d+\s*[x×]\s*\d+", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\b\d+\b", " ", cleaned)
    cleaned = re.sub(r"\b(sets?|reps?|with|did|do|performed|of|for|and|x|×|@)\b", " ", cleaned, flags=re.I)
    ex = re.sub(r"\s+", " ", cleaned).strip().lower()
    if not ex:
        return None
    return {"exercise": ex, "sets": sets, "reps": reps, "weight": weight}

def regex_parse(text: str) -> List[dict]:
    parts = EX_SPLIT_RE.split(text)
    out = []
    for piece in parts:
        item = parse_piece(piece)
        if item:
            out.append(item)
    return out

def extract_json(raw: str):
    if not raw:
        return None
    m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.S | re.I)
    if m:
        raw = m.group(1).strip()
    try:
        import json as _json
        return _json.loads(raw)
    except Exception:
        pass
    blobs = []
    stack = []
    start = None
    in_str = False
    esc = False
    for i, ch in enumerate(raw):
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': in_str = False
            continue
        if ch == '"':
            in_str = True; continue
        if ch in "{[": 
            if not stack: start = i
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if stack and ch == stack[-1]:
                stack.pop()
                if not stack and start is not None:
                    blobs.append(raw[start:i+1]); start = None
    def try_load_candidates(text: str):
        candidates = [text, re.sub(r",\s*([}\]])", r"\1", text)]
        for cand in candidates:
            try:
                return json.loads(cand)
            except Exception:
                try:
                    inner = json.loads(cand)
                    if isinstance(inner, (str, bytes)):
                        return json.loads(inner)
                except Exception:
                    pass
        return None
    parsed = []
    for b in blobs:
        obj = try_load_candidates(b)
        if obj is not None:
            parsed.append(obj)
    if not parsed:
        return None
    if len(parsed) == 1:
        return parsed[0]
    return parsed
