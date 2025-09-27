import streamlit as st
import pandas as pd
import datetime
import json
import re

from db import init_db, get_workouts, save_workout, clear_workouts, delete_last_entry, delete_by_id
from parsing import normalize_date, normalize_value, regex_parse, extract_json
from llm import call_ollama

st.set_page_config(page_title="AI Personal Trainer", page_icon="💪", layout="wide")
st.title("💪 AI Personal Trainer (Offline)")

init_db()

tab1, tab2, tab3 = st.tabs(["📓 Workout Logs", "📊 Analytics", "🧑‍🏫 AI Coach"])

def parse_reps_cell(v):
    if v is None:
        return None
    if isinstance(v, (int, float, list)):
        return v
    s = str(v)
    try:
        obj = json.loads(s)
        return obj
    except Exception:
        m = re.fullmatch(r"\s*-?\d+\s*", s)
        if m:
            return int(s)
        return s

def reps_to_str(v):
    r = parse_reps_cell(v)
    if r is None:
        return "—"
    if isinstance(r, list):
        return ",".join(str(int(x)) for x in r)
    if isinstance(r, (int, float)):
        return str(int(r))
    return str(r)

# -------- Tab 1: Logs --------
with tab1:
    st.subheader("Log your workout in plain English")

    log_input = st.text_area(
        "Enter workout:",
        placeholder="e.g., Did 3 sets of 10 pushups and 2 sets of squats with 20kg",
    )
    col_log = st.columns(6)
    btn_log = col_log[0].button("Log Workout")
    btn_undo = col_log[1].button("Undo Last Entry")
    delete_row_no = col_log[2].number_input("Delete by row #", min_value=1, step=1, value=1)
    btn_delete_row = col_log[3].button("Delete Row")
    del_type = col_log[4].text_input("Delete by workout type", placeholder="e.g., bench press")
    btn_delete_type = col_log[5].button("Delete Type")

    if btn_undo:
        delete_last_entry()
        st.success("Last entry deleted.")

    if btn_delete_row:
        st.session_state["__delete_row_req__"] = int(delete_row_no)
        st.success(f"Requested delete of row #{int(delete_row_no)} — will apply below.")

    if btn_delete_type and del_type:
        clear_workouts(del_type.strip().lower())
        st.success(f"Deleted all workouts of type '{del_type}'.")

    if st.button("🧹 Clear All Workouts"):
        clear_workouts()
        st.success("All workouts cleared.")

    if btn_log and log_input.strip():
        prompt = f"""
You are a workout log parser.
Parse the following natural language workout description into structured JSON objects.

Text: "{log_input}"

Rules:
- Output ONLY valid JSON (array if multiple exercises).
- Each object must follow this schema:
  {{
    "date": "YYYY-MM-DD" | "today" | "yesterday",
    "exercise": "string",
    "sets": int | null,
    "reps": int | list[int] | null,
    "weight": float | null
  }}
- Notes:
  * If reps vary (e.g., "4,5,6,6") -> use a list of integers.
  * If sets are implied by the count of reps values, set "sets" accordingly.
  * If only reps are given without sets, leave "sets": null and store reps as a list.
  * If weight is mentioned, return only the number in kg (convert lbs to kg).
  * Handle dates naturally: "today", "yesterday", or explicit dates like "21/09/2024".
  * Do not invent missing info — use null instead.
- Today’s date is {datetime.date.today()}.
"""
        entries = []
        res = call_ollama(prompt)
        if res["ok"] and res["stdout"]:
            parsed = extract_json(res["stdout"])
            if parsed:
                entries = parsed if isinstance(parsed, list) else [parsed]

        if not entries:
            entries = regex_parse(log_input)

        logged = []
        for e in entries:
            if not isinstance(e, dict):
                continue
            ex = str(e.get("exercise", "")).strip().lower()
            if not ex:
                continue

            reps_norm = normalize_value(e.get("reps"))
            sets_norm = normalize_value(e.get("sets"))
            weight_norm = normalize_value(e.get("weight"), as_float=True)

            if isinstance(reps_norm, list) and (sets_norm is None):
                sets_norm = len(reps_norm)

            rec = {
                "date": normalize_date(e.get("date")) or datetime.date.today().isoformat(),
                "exercise": ex,
                "sets": sets_norm,
                "reps": reps_norm,
                "weight": weight_norm,
            }
            save_workout(rec)
            logged.append(rec)

        if logged:
            show = []
            for r in logged:
                show.append({
                    "date": r["date"],
                    "exercise": r["exercise"],
                    "sets": r["sets"],
                    "reps": r["reps"] if not isinstance(r["reps"], list) else ",".join(map(str, r["reps"])),
                    "weight (kg)": r["weight"],
                })
            st.success(f"Logged {len(logged)} entr{'y' if len(logged)==1 else 'ies'}.")
            st.json(show)
        else:
            st.warning("⚠️ Couldn't understand that. Try: 'bench press 5x5 @ 100kg' or '4 sets pushups with reps 4,5,6,6'.")

    st.subheader("Workout History")
    rows = get_workouts()
    if rows:
        df = pd.DataFrame(rows, columns=["id", "date", "exercise", "sets", "reps", "weight"])
        df = df.reset_index(drop=True)
        df["row_no"] = df.index + 1
        view = df.copy()

        def reps_disp(v):
            try:
                obj = json.loads(v) if isinstance(v, str) else v
            except Exception:
                obj = v
            if obj is None:
                return "—"
            if isinstance(obj, list):
                return ",".join(str(int(x)) for x in obj)
            if isinstance(obj, (int, float)):
                return str(int(obj))
            s = str(obj)
            m = re.fullmatch(r"\\s*-?\\d+\\s*", s)
            return s.strip() if not m else str(int(s))
        view["reps"] = view["reps"].apply(reps_disp)
        view["weight"] = view["weight"].apply(lambda x: f"{x:.0f} kg" if pd.notnull(x) else "—")
        view = view[["row_no", "date", "exercise", "sets", "reps", "weight"]]
        st.dataframe(view, use_container_width=True)

        req = st.session_state.pop("__delete_row_req__", None)
        if req is not None:
            match = df[df["row_no"] == int(req)]
            if not match.empty:
                row_id = int(match.iloc[0]["id"])
                delete_by_id(row_id)
                st.success(f"Deleted row #{int(req)} (id={row_id}). Please refresh view.")
            else:
                st.warning(f"Row #{int(req)} not found in current table.")

        st.download_button("⬇️ Export CSV", data=view.to_csv(index=False).encode("utf-8"),
                           file_name="workouts.csv", mime="text/csv")
    else:
        st.info("No workouts logged yet.")

# -------- Tab 2: Analytics --------
with tab2:
    st.subheader("Progress & Analytics")

    rows = get_workouts()
    if not rows:
        st.info("Log some workouts to see analytics.")
    else:
        df = pd.DataFrame(rows, columns=["id", "date", "exercise", "sets", "reps", "weight"]).drop(columns=["id"])
        def parse_reps_cell_local(v):
            if v is None:
                return None
            try:
                obj = json.loads(v) if isinstance(v, str) else v
            except Exception:
                obj = v
            return obj
        df["reps_parsed"] = df["reps"].apply(parse_reps_cell_local)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date")

        ex_list = sorted(df["exercise"].dropna().unique().tolist())
        sel_ex = st.selectbox("Select exercise", options=["(All)"] + ex_list, index=0)

        def compute_volume(row):
            w = row["weight"]
            s = row["sets"]
            r = row["reps_parsed"]
            if pd.isna(w):
                return None
            try:
                if isinstance(r, list):
                    return float(w) * float(sum(int(x) for x in r))
                if r is not None and s is not None:
                    return float(w) * float(int(r)) * float(int(s))
            except Exception:
                return None
            return None
        df["volume"] = df.apply(compute_volume, axis=1)

        if sel_ex != "(All)":
            ex_df = df[df["exercise"] == sel_ex].copy()
        else:
            ex_df = df.copy()

        colA, colB, colC = st.columns(3)
        pr = ex_df["weight"].max() if not ex_df.empty else None
        training_days = ex_df.groupby("date").size().shape[0] if not ex_df.empty else 0
        total_volume = ex_df["volume"].sum() if not ex_df.empty else 0.0

        colA.metric("Heaviest Weight (PR)", f"{int(pr)} kg" if pd.notnull(pr) else "—")
        colB.metric("Training Days", f"{training_days}")
        colC.metric("Total Volume", f"{int(total_volume):,}" if total_volume else "—")

        st.write("### Weight over time")
        if ex_df["weight"].notna().any():
            st.line_chart(ex_df.set_index("date")["weight"])

        st.write("### Volume over time")
        if ex_df["volume"].notna().any():
            st.line_chart(ex_df.set_index("date")["volume"])

        st.write("### Sessions per week")
        sessions = ex_df.copy()
        sessions["week"] = sessions["date"].dt.to_period("W").apply(lambda r: r.start_time)
        weekly = sessions.groupby("week").size().rename("sessions")
        if not weekly.empty:
            st.bar_chart(weekly)

# -------- Tab 3: AI Coach --------
with tab3:
    st.subheader("Ask your AI coach")

    q = st.text_input("Your question:", placeholder="e.g., What should I focus on next week based on my progress?")
    if st.button("Ask Coach"):
        if q.strip():
            rows = get_workouts()
            df = pd.DataFrame(rows, columns=["id", "date", "exercise", "sets", "reps", "weight"]).drop(columns=["id"])

            def parse_reps_cell_local(v):
                if v is None:
                    return None
                try:
                    obj = json.loads(v) if isinstance(v, str) else v
                except Exception:
                    obj = v
                return obj

            df["reps_parsed"] = df["reps"].apply(parse_reps_cell_local)
            df_sorted = df.sort_values("date")
            context_rows = df_sorted.tail(200).to_dict(orient="records")
            for r in context_rows:
                r["reps"] = r.pop("reps_parsed")
            for r in context_rows:
                if "reps" in r and isinstance(r["reps"], str):
                    try:
                        r["reps"] = json.loads(r["reps"])
                    except Exception:
                        pass

            context_json = json.dumps(context_rows, ensure_ascii=False)

            coach_prompt = f"""
You are a certified health & fitness coach. You are given a user's workout log as JSON records from their database.
Use this data to answer the user's question. Be specific and data-driven when referencing their history.
If the question requires advice (programming, recovery, progression), combine best-practice coaching principles with insights from their data.
If the user asks about exact numbers or history, rely ONLY on the provided data. If something isn't in the data, say you don't have it.

WORKOUT_LOG_JSON = {context_json}

User question: "{q}"

Constraints:
- Answer in 3-7 sentences unless the user explicitly asks for more detail.
- When citing facts (dates, sets, reps, weights), use the numbers in WORKOUT_LOG_JSON.
- If making recommendations, tie them back to trends or gaps you see in the data.
"""

            res = call_ollama(coach_prompt, timeout=60)
            if res["ok"]:
                st.markdown(f"*Coach:* {res['stdout']}")
            else:
                st.error(f"LLM call failed: {res['stderr']}")
