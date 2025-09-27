import streamlit as st
import pandas as pd
import datetime
import json
import re

from db import init_db, get_workouts, save_workout, clear_workouts, delete_last_entry, delete_by_id
from parsing import normalize_date, normalize_value, regex_parse, extract_json
from llm2 import call_huggingface, setup_api_key_ui

st.set_page_config(page_title="AI Personal Trainer (Cloud)", page_icon="💪", layout="wide")
st.title("💪 AI Personal Trainer (Cloud Version)")

# Initialize database
init_db()

# Setup API key if needed
setup_api_key_ui()

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
Convert to workout JSON: "{log_input}"

Required JSON fields:
date: YYYY-MM-DD/today/yesterday
exercise: name
sets: number/null
reps: number/[numbers]/null
weight: kg/null

Rules:
- Multiple exercises → array
- Varying reps → [4,5,6,6]
- lbs → kg (×0.453592)
- Missing info → null
- Today: {datetime.date.today()}

Example format:
{{"date":"today", "exercise":"pushups", "sets":3, "reps":10, "weight":null}}

Return clean JSON only.
"""
        # Call Hugging Face API
        result = call_huggingface(prompt)
        
        if not result["ok"]:
            st.error(f"Error: {result['error']}")
        else:
            try:
                # Parse the workout data
                entries = json.loads(result["output"])
                if not isinstance(entries, list):
                    entries = [entries]
                
                # Save each entry to the database
                for entry in entries:
                    if isinstance(entry, dict) and "exercise" in entry:
                        save_workout(entry)
                
                st.success("Workout logged successfully! 💪")
            except Exception as e:
                st.error(f"Failed to parse response: {str(e)}")

    # Display workout history
    rows = get_workouts()
    if rows:
        df = pd.DataFrame(rows, columns=["id", "date", "exercise", "sets", "reps", "weight"])
        
        # Format the dataframe
        df["reps"] = df["reps"].apply(reps_to_str)
        df["sets"] = df["sets"].apply(lambda x: "—" if x is None else str(int(x)))
        df["weight"] = df["weight"].apply(lambda x: "—" if x is None else f"{x}kg")
        
        # Handle row deletion requests
        if "__delete_row_req__" in st.session_state:
            row_id = st.session_state["__delete_row_req__"]
            if 1 <= row_id <= len(df):
                delete_by_id(int(df.iloc[row_id-1]["id"]))
                del st.session_state["__delete_row_req__"]
                st.rerun()
        
        # Display the table
        st.dataframe(
            df.drop("id", axis=1),
            column_config={
                "date": "Date",
                "exercise": "Exercise",
                "sets": "Sets",
                "reps": "Reps",
                "weight": "Weight"
            },
            hide_index=False
        )
    else:
        st.info("No workouts logged yet. Start by entering a workout above!")

# -------- Tab 2: Analytics --------
with tab2:
    st.info("Analytics features coming soon! 📊")

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
            context_rows = df_sorted.tail(50).to_dict(orient="records")  # Last 50 workouts
            for r in context_rows:
                r["reps"] = r.pop("reps_parsed")

            context_json = json.dumps(context_rows, ensure_ascii=False)
            
            coach_prompt = f"""Role: Expert fitness coach
Workout history: {context_json}
Question: {q}

Analyze the workout data and answer the question. Focus on:
1. Recent patterns and trends
2. Progress indicators
3. Specific advice based on data
4. Clear, actionable recommendations

Keep response under 5 sentences. Use numbers from data when relevant."""

            res = call_huggingface(coach_prompt, timeout=45)
            if res["ok"]:
                st.markdown(f"*Coach:* {res['output']}")
            else:
                st.error(f"Unable to reach AI coach: {res['error']}")