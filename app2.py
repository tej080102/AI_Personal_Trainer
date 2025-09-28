
import streamlit as st
import pandas as pd
import datetime
import json
import re
import plotly.express as px

from db import (
    init_db, get_workouts, save_workout, clear_workouts,
    delete_last_entry, delete_by_id, create_user, check_user
)
from llm2 import call_huggingface, setup_api_key_ui

st.set_page_config(page_title="AI Personal Trainer", page_icon="💪", layout="wide")
st.title("💪 AI Personal Trainer (Hugging Face + Llama-3.1-8B-Instruct)")

# Initialize database
init_db()

# --- Authentication ---
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None
if "auth_mode" not in st.session_state:
    st.session_state["auth_mode"] = "login"

if not st.session_state["user_id"]:
    st.sidebar.title("Authentication")
    mode = st.sidebar.radio("Choose mode:", ["Login", "Sign Up"])
    st.session_state["auth_mode"] = "signup" if mode == "Sign Up" else "login"

    with st.form("auth_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Submit")

        if submitted and username.strip() and password.strip():
            if st.session_state["auth_mode"] == "signup":
                create_user(username.strip(), password.strip())
                st.success("✅ Account created! Please log in.")
            else:
                if check_user(username.strip(), password.strip()):
                    st.session_state["user_id"] = username.strip()
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password.")
    st.stop()

user_id = st.session_state["user_id"]
st.sidebar.success(f"Logged in as: {user_id}")
if st.sidebar.button("Logout"):
    st.session_state["user_id"] = None
    st.rerun()

# Setup Hugging Face API key
setup_api_key_ui()

tab1, tab2, tab3 = st.tabs(["📓 Workout Logs", "📊 Analytics", "🧑‍🏫 AI Coach"])

# ---------------- Helper Functions ---------------- #
def parse_reps_cell(v):
    if v is None:
        return None
    if isinstance(v, list):
        return v
    if isinstance(v, (int, float)):
        return v if not pd.isna(v) else None
    s = str(v).strip()
    try:
        return json.loads(s)
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
        return ",".join(str(int(x)) for x in r if x is not None and not pd.isna(x))
    if isinstance(r, (int, float)):
        if pd.isna(r):
            return "—"
        return str(int(r))
    return str(r)

def normalize_date_field(d):
    if not d or not isinstance(d, str):
        return d
    d0 = d.lower().strip()
    if d0 == "today":
        return str(datetime.date.today())
    if d0 == "yesterday":
        return str(datetime.date.today() - datetime.timedelta(days=1))
    return d

# ---------------- Tab 1: Logs ---------------- #
with tab1:
    st.subheader("Log your workout in plain English")
    log_input = st.text_area(
        "Enter workout:",
        placeholder="e.g., 10 pushups, 50kg incline press 3 sets, 5 km run in 25 min",
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    btn_log = c1.button("Log Workout")
    btn_undo = c2.button("Undo Last Entry")
    delete_row_no = c3.number_input("Delete by row #", min_value=1, step=1, value=1)
    btn_delete_row = c4.button("Delete Row")
    del_type = c5.text_input("Delete by workout type", placeholder="e.g., bench press")
    btn_delete_type = c6.button("Delete Type")

    if btn_undo:
        delete_last_entry(user_id)
        st.success("Deleted last entry.")
    if btn_delete_row:
        st.session_state["__del_req__"] = int(delete_row_no)
        st.success(f"Requested deletion of row #{int(delete_row_no)}")
    if btn_delete_type and del_type:
        clear_workouts(exercise=del_type.strip().lower(), user_id=user_id)
        st.success(f"Deleted all {del_type}")
    if st.button("Clear All Workouts"):
        clear_workouts(user_id=user_id)
        st.success("Cleared all workouts")

    if btn_log and log_input.strip():
        prompt = f'''
You are a workout & cardio parser. Convert the following text into JSON.

Text: "{log_input}"

Output is a list of objects, each with keys:
- date: YYYY-MM-DD or today/yesterday
- exercise: string
- sets: integer or null
- reps: integer, list, or null
- weight: integer (kg) or null
- distance: float (km) or null
- duration: float (minutes) or null
- notes: string or empty

Return JSON only.
'''
        result = call_huggingface(prompt)
        if not result["ok"]:
            st.error(f"Error: {result['error']}")
        else:
            try:
                entries = json.loads(result["output"])
                if not isinstance(entries, list):
                    entries = [entries]
                for e in entries:
                    if not isinstance(e, dict) or "exercise" not in e:
                        continue
                    e["date"] = normalize_date_field(e.get("date"))
                    e["user_id"] = user_id
                    save_workout(e)
                st.success("Logged successfully! 💪")
            except Exception as e:
                st.error(f"Parse error: {e}")

    rows = get_workouts(user_id)
    if rows:
        df = pd.DataFrame(
            rows,
            columns=["id", "date", "exercise", "sets", "reps", "weight", "distance", "duration"],
        )
        df["reps"] = df["reps"].apply(reps_to_str)
        df["sets"] = df["sets"].apply(lambda x: "—" if x is None or pd.isna(x) else str(int(x)))
        df["weight"] = df["weight"].apply(lambda x: "—" if x is None or pd.isna(x) else f"{int(x)}kg")
        df["distance"] = df["distance"].apply(lambda x: "—" if x is None or pd.isna(x) else f"{float(x):.2f} km")
        df["duration"] = df["duration"].apply(lambda x: "—" if x is None or pd.isna(x) else f"{float(x):.1f} min")

        if "__del_req__" in st.session_state:
            rid = st.session_state["__del_req__"]
            if 1 <= rid <= len(df):
                delete_by_id(int(df.iloc[rid - 1]["id"]), user_id)
                del st.session_state["__del_req__"]
                st.rerun()

        display_df = df.drop("id", axis=1).reset_index(drop=True).rename(lambda x: x + 1)
        st.dataframe(display_df)
    else:
        st.info("No workouts yet.")

# ---------------- Tab 2: Analytics ---------------- #
with tab2:
    st.subheader("📊 Analytics")
    rows = get_workouts(user_id)
    if not rows:
        st.info("No data to analyze yet.")
    else:
        df = pd.DataFrame(
            rows,
            columns=["id", "date", "exercise", "sets", "reps", "weight", "distance", "duration"],
        )
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

        # This Week Split
        this_week = df[df["date"] >= (pd.Timestamp.today() - pd.Timedelta(days=7))]
        strength_sessions = this_week[this_week["weight"].notna()].shape[0]
        cardio_sessions = this_week[(this_week["distance"].notna()) | (this_week["duration"].notna())].shape[0]
        split_df = pd.DataFrame({"Type": ["Strength", "Cardio"], "Count": [strength_sessions, cardio_sessions]})
        st.plotly_chart(px.pie(split_df, names="Type", values="Count", hole=0.4))

        # Progress Over Time (Volume + Cardio)
        st.write("### Progress Over Time")
        all_exercises = ["All"] + sorted(df["exercise"].dropna().unique().tolist())
        selected_ex = st.selectbox("Select Exercise", all_exercises, index=0)

        # Strength
        strength_df = df.dropna(subset=["weight", "sets", "reps"])
        strength_df = strength_df[strength_df["weight"] > 0]
        if not strength_df.empty:
            def calc_volume(row):
                try:
                    reps = json.loads(row["reps"]) if isinstance(row["reps"], str) else row["reps"]
                    if isinstance(reps, list):
                        reps = sum(int(r) for r in reps if r is not None)
                    elif reps is None:
                        reps = 0
                    return row["sets"] * reps * row["weight"] if reps and row["weight"] else None
                except Exception:
                    return None
            strength_df = strength_df.copy()
            strength_df["volume"] = strength_df.apply(calc_volume, axis=1)
            vol_grouped = strength_df.groupby(["date", "exercise"])["volume"].sum().reset_index()
            if selected_ex != "All":
                vol_grouped = vol_grouped[vol_grouped["exercise"] == selected_ex]
            if not vol_grouped.empty:
                st.plotly_chart(px.line(vol_grouped, x="date", y="volume", color="exercise" if selected_ex=="All" else None))

        # Cardio
        cardio_df = df.dropna(subset=["distance", "duration"])
        if not cardio_df.empty:
            cardio_df = cardio_df.copy()
            cardio_df["pace"] = cardio_df["duration"] / cardio_df["distance"]
            option = st.radio("Cardio metric:", ["Distance", "Pace"], horizontal=True)
            card = cardio_df if selected_ex == "All" else cardio_df[cardio_df["exercise"] == selected_ex]
            if not card.empty:
                if option == "Distance":
                    st.plotly_chart(px.line(card, x="date", y="distance", color="exercise" if selected_ex=="All" else None))
                else:
                    st.plotly_chart(px.line(card, x="date", y="pace", color="exercise" if selected_ex=="All" else None))

        # PRs
        st.write("### Personal Records (PRs)")
        prs = {}
        for ex in df["exercise"].unique():
            ex_df = df[df["exercise"] == ex]
            if ex_df["weight"].notna().sum() > 0:
                prs[ex] = f"{ex_df['weight'].max()} kg"
            elif ex_df["distance"].notna().sum() > 0:
                prs[ex] = f"{ex_df['distance'].max()} km"
            elif ex_df["duration"].notna().sum() > 0:
                prs[ex] = f"{ex_df['duration'].max()} min"
        if prs:
            st.table(pd.DataFrame(list(prs.items()), columns=["Exercise", "PR"]))

# ---------------- Tab 3: AI Coach ---------------- #
with tab3:
    st.subheader("Ask your AI coach")
    with st.form("coach_form", clear_on_submit=True):
        q = st.text_input("Your question:", placeholder="e.g., What should I eat after today's workout?")
        submitted = st.form_submit_button("Ask Coach")
        if submitted and q.strip():
            rows = get_workouts(user_id)
            df = pd.DataFrame(rows, columns=["id","date","exercise","sets","reps","weight","distance","duration"]).drop(columns=["id"], errors="ignore")
            def parse_reps(v):
                try:
                    return json.loads(v) if isinstance(v,str) else v
                except Exception:
                    return v
            df["reps"] = df["reps"].apply(parse_reps)
            context = df.sort_values("date").tail(50).to_dict(orient="records")
            context_json = json.dumps(context, ensure_ascii=False)
            coach_prompt = f"""Role: Expert fitness coach (training, nutrition, injury, form).
Workout history for {user_id}: {context_json}
User question: {q}
- Be concise (≤6 sentences). If injury → add consult disclaimer.
"""
            res = call_huggingface(coach_prompt)
            if res["ok"]:
                st.markdown(f"*Coach:* {res['output']}")
            else:
                st.error(res["error"])




