"""
AI Personal Trainer - Streamlit Frontend
Full-featured UI with Dashboard, Workout Logs, Analytics, AI Coach, and more.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import json
import os

from api_client import APIClient

# ============= Configuration ============= #

st.set_page_config(
    page_title="AI Personal Trainer",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API URL - defaults to Docker service name
API_URL = os.getenv("API_URL", "http://api:8000")

# Initialize API client
@st.cache_resource
def get_client():
    return APIClient(API_URL)

client = get_client()

# ============= Session State ============= #

if "token" not in st.session_state:
    st.session_state["token"] = None
if "user" not in st.session_state:
    st.session_state["user"] = None
if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = True

# Apply token to client
if st.session_state["token"]:
    client.token = st.session_state["token"]


# ============= Dark Mode ============= #

def apply_dark_mode():
    """Apply dark mode styling."""
    if st.session_state["dark_mode"]:
        st.markdown("""
        <style>
        .stApp {
            background-color: #0e1117;
            color: #fafafa;
        }
        .stat-card {
            background: linear-gradient(135deg, #1a1f2e 0%, #252a3a 100%);
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
            border: 1px solid #333;
        }
        .stat-value {
            font-size: 2.5rem;
            font-weight: bold;
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stat-label {
            font-size: 0.9rem;
            color: #888;
            margin-top: 0.5rem;
        }
        .safe-badge {
            background-color: #10b981;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
        }
        .unsafe-badge {
            background-color: #ef4444;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
        }
        </style>
        """, unsafe_allow_html=True)

apply_dark_mode()


# ============= Authentication ============= #

def show_auth_page():
    """Show login/signup page."""
    st.title("💪 AI Personal Trainer")
    st.markdown("### Intelligent workout planning with safety-first AI")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login", use_container_width=True)
                
                if submitted and username and password:
                    try:
                        result = client.login(username, password)
                        st.session_state["token"] = result["access_token"]
                        st.session_state["user"] = client.get_me()
                        st.success("✅ Login successful!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ {e}")
        
        with tab2:
            with st.form("signup_form"):
                new_username = st.text_input("Username", key="signup_user")
                email = st.text_input("Email")
                new_password = st.text_input("Password", type="password", key="signup_pass")
                confirm_password = st.text_input("Confirm Password", type="password")
                submitted = st.form_submit_button("Sign Up", use_container_width=True)
                
                if submitted:
                    if new_password != confirm_password:
                        st.error("❌ Passwords don't match!")
                    elif new_username and email and new_password:
                        try:
                            client.signup(new_username, email, new_password)
                            st.success("✅ Account created! Please log in.")
                        except Exception as e:
                            st.error(f"❌ {e}")


# ============= Dashboard ============= #

def show_dashboard():
    """Show dashboard with summary cards."""
    st.header("📊 Dashboard")
    
    try:
        stats = client.get_workout_stats()
        plan_stats = client.get_plan_stats()
    except:
        stats = {"total_workouts": 0, "this_week": 0, "total_volume_kg": 0, 
                 "total_distance_km": 0, "current_streak": 0, "exercises_count": 0}
        plan_stats = {"total_plans": 0, "avg_latency_ms": 0}
    
    # Summary Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats.get('total_workouts', 0)}</div>
            <div class="stat-label">Total Workouts</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats.get('current_streak', 0)}</div>
            <div class="stat-label">Day Streak 🔥</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats.get('this_week', 0)}</div>
            <div class="stat-label">This Week</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{plan_stats.get('total_plans', 0)}</div>
            <div class="stat-label">AI Plans Generated</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Second row
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Volume Progress")
        try:
            workouts = client.get_workouts(limit=50)
            if workouts:
                df = pd.DataFrame(workouts)
                df['date'] = pd.to_datetime(df['date'])
                
                # Group by date
                daily = df.groupby(df['date'].dt.date).size().reset_index(name='count')
                
                fig = px.bar(daily, x='date', y='count', 
                            title="Workouts per Day",
                            color_discrete_sequence=['#7c3aed'])
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No workout data yet. Start logging!")
        except Exception as e:
            st.warning(f"Could not load chart: {e}")
    
    with col2:
        st.subheader("🏃 Quick Stats")
        st.metric("Total Volume", f"{stats.get('total_volume_kg', 0):,.0f} kg")
        st.metric("Total Distance", f"{stats.get('total_distance_km', 0):.1f} km")
        st.metric("Exercise Variety", f"{stats.get('exercises_count', 0)} types")


# ============= Workout Logs ============= #

def show_workout_logs():
    """Show workout logging tab."""
    st.header("📓 Workout Logs")
    
    # Log new workout
    st.subheader("Log New Workout")
    
    with st.form("log_workout"):
        col1, col2 = st.columns(2)
        
        with col1:
            exercise = st.text_input("Exercise", placeholder="e.g., Bench Press, Running")
            workout_date = st.date_input("Date", value=date.today())
            sets = st.number_input("Sets", min_value=0, value=3)
            reps = st.text_input("Reps", placeholder="e.g., 10 or 10,8,6")
        
        with col2:
            weight = st.number_input("Weight (kg)", min_value=0.0, step=2.5)
            distance = st.number_input("Distance (km)", min_value=0.0, step=0.5)
            duration = st.number_input("Duration (min)", min_value=0.0, step=1.0)
            notes = st.text_input("Notes", placeholder="Optional notes")
        
        submitted = st.form_submit_button("💾 Log Workout", use_container_width=True)
        
        if submitted and exercise:
            try:
                workout = {
                    "date": str(workout_date),
                    "exercise": exercise,
                    "sets": sets if sets > 0 else None,
                    "reps": reps if reps else None,
                    "weight": weight if weight > 0 else None,
                    "distance": distance if distance > 0 else None,
                    "duration": duration if duration > 0 else None,
                    "notes": notes if notes else None
                }
                client.create_workout(workout)
                st.success("✅ Workout logged!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ {e}")
    
    st.markdown("---")
    
    # Workout history
    st.subheader("Workout History")
    
    try:
        workouts = client.get_workouts(limit=100)
        if workouts:
            # Header row
            cols = st.columns([1.2, 1.5, 0.7, 0.7, 0.9, 0.9, 0.9, 0.5])
            headers = ["date", "exercise", "sets", "reps", "weight", "distance", "duration", ""]
            for col, header in zip(cols, headers):
                col.markdown(f"**{header}**")
            
            st.markdown("<hr style='margin:0.2rem 0; border-color:#333;'>", unsafe_allow_html=True)
            
            # Data rows with delete button
            for w in workouts:
                cols = st.columns([1.2, 1.5, 0.7, 0.7, 0.9, 0.9, 0.9, 0.5])
                w_date = pd.to_datetime(w['date']).strftime('%Y-%m-%d')
                cols[0].write(w_date)
                cols[1].write(w.get('exercise', '—'))
                cols[2].write(w['sets'] if w.get('sets') else "—")
                cols[3].write(w['reps'] if w.get('reps') else "—")
                cols[4].write(f"{w['weight']}kg" if w.get('weight') and w['weight'] > 0 else "—")
                cols[5].write(f"{w['distance']}km" if w.get('distance') and w['distance'] > 0 else "—")
                cols[6].write(f"{w['duration']}min" if w.get('duration') and w['duration'] > 0 else "—")
                if cols[7].button("🗑️", key=f"del_w_{w['id']}"):
                    client.delete_workout(w['id'])
                    st.rerun()
            
            st.markdown("---")
            
            # Clear all button
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Clear All Workouts"):
                    client.clear_workouts()
                    st.rerun()
        else:
            st.info("No workouts logged yet.")
    except Exception as e:
        st.error(f"Failed to load workouts: {e}")


# ============= Analytics ============= #

def show_analytics():
    """Show analytics tab with charts."""
    st.header("📊 Analytics")
    
    try:
        workouts = client.get_workouts(limit=200)
        if not workouts:
            st.info("No data to analyze yet. Start logging workouts!")
            return
        
        df = pd.DataFrame(workouts)
        df['date'] = pd.to_datetime(df['date'])
        
        # Training Split
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Training Split (This Week)")
            week_ago = datetime.now() - timedelta(days=7)
            this_week = df[df['date'] >= week_ago]
            
            if not this_week.empty:
                strength = this_week[this_week['weight'].notna()].shape[0]
                cardio = this_week[(this_week['distance'].notna()) | (this_week['duration'].notna())].shape[0]
                
                fig = px.pie(
                    values=[strength, cardio],
                    names=['Strength', 'Cardio'],
                    color_discrete_sequence=['#7c3aed', '#00d4ff'],
                    hole=0.4
                )
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No workouts this week")
        
        with col2:
            st.subheader("Exercise Distribution")
            exercise_counts = df['exercise'].value_counts().head(10)
            
            fig = px.bar(
                x=exercise_counts.values,
                y=exercise_counts.index,
                orientation='h',
                color_discrete_sequence=['#7c3aed']
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                yaxis_title="",
                xaxis_title="Count"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Progress Over Time
        st.subheader("Progress Over Time")
        
        exercises = ["All"] + sorted(df['exercise'].unique().tolist())
        selected_exercise = st.selectbox("Select Exercise", exercises)
        
        if selected_exercise != "All":
            chart_df = df[df['exercise'] == selected_exercise].copy()
        else:
            chart_df = df.copy()
        
        # Strength progress
        strength_df = chart_df[chart_df['weight'].notna() & (chart_df['weight'] > 0)]
        
        if not strength_df.empty:
            fig = px.line(
                strength_df,
                x='date',
                y='weight',
                color='exercise' if selected_exercise == "All" else None,
                title="Weight Progress"
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Personal Records
        st.subheader("🏆 Personal Records")
        
        prs = []
        for ex in df['exercise'].unique():
            ex_df = df[df['exercise'] == ex]
            if ex_df['weight'].notna().any():
                prs.append({"Exercise": ex, "PR": f"{ex_df['weight'].max():.0f} kg"})
            elif ex_df['distance'].notna().any():
                prs.append({"Exercise": ex, "PR": f"{ex_df['distance'].max():.1f} km"})
        
        if prs:
            st.dataframe(pd.DataFrame(prs), use_container_width=True, hide_index=True)
        
    except Exception as e:
        st.error(f"Failed to load analytics: {e}")


# ============= AI Coach ============= #

def show_ai_coach():
    """Show AI Coach tab with LangGraph workout planning."""
    st.header("🧑‍🏫 AI Coach")
    
    st.markdown("""
    Generate a personalized, **safety-validated** workout plan using our multi-agent AI system.
    The system uses LangGraph with a **Physiotherapist Safety Loop** to ensure exercises are 
    appropriate for your injuries.
    """)
    
    # User Profile
    st.subheader("Your Profile")
    
    col1, col2 = st.columns(2)
    
    with col1:
        goals = st.text_area("Fitness Goals", placeholder="e.g., Build muscle, lose weight, improve endurance")
        fitness_level = st.selectbox("Fitness Level", ["beginner", "intermediate", "advanced"])
    
    with col2:
        age = st.number_input("Age", min_value=10, max_value=100, value=30)
        weight = st.number_input("Weight (kg)", min_value=30.0, max_value=300.0, value=70.0)
        equipment = st.multiselect("Equipment Available", 
                                   ["bodyweight", "dumbbells", "barbell", "kettlebell", 
                                    "pull-up bar", "bench", "cables", "machines", "full gym"])
    
    # Injuries
    st.subheader("Injury Profile")
    st.markdown("*Active injuries will be considered when generating your plan*")
    
    try:
        injuries = client.get_injuries(active_only=True)
        if injuries:
            injury_df = pd.DataFrame(injuries)[['injury_type', 'severity', 'notes']]
            st.dataframe(injury_df, use_container_width=True, hide_index=True)
        else:
            st.info("No active injuries. Add injuries in the Injury Profile section.")
    except:
        injuries = []
        st.info("Could not load injuries.")
    
    st.markdown("---")
    
    # Generate Plan
    if st.button("🚀 Generate My Workout Plan", type="primary", use_container_width=True):
        if not goals:
            st.error("Please enter your fitness goals")
            return
        
        with st.spinner("🤖 AI is generating your personalized plan..."):
            progress = st.progress(0)
            status = st.empty()
            
            import time
            start_time = time.time()
            
            status.text("🔄 Trainer agent drafting initial plan...")
            progress.progress(25)
            
            try:
                user_profile = {
                    "goals": goals,
                    "fitness_level": fitness_level,
                    "age": age,
                    "weight": weight,
                    "equipment_available": equipment
                }
                
                # Convert injuries for API
                injury_history = []
                for inj in injuries:
                    injury_history.append({
                        "injury_type": inj["injury_type"],
                        "injury_date": inj["injury_date"][:10] if inj["injury_date"] else "2024-01-01",
                        "severity": inj["severity"],
                        "notes": inj.get("notes", "")
                    })
                
                thread_id = f"user_{st.session_state['user']['id']}_{int(time.time())}"
                
                progress.progress(50)
                status.text("🩺 Physiotherapist reviewing for safety...")
                
                result = client.generate_plan(user_profile, injury_history, thread_id)
                
                elapsed = time.time() - start_time
                progress.progress(100)
                status.text(f"✅ Plan generated in {elapsed:.1f}s")
                
                # Display result
                st.success(f"🎉 **Plan Generated!** Revisions: {result.get('revision_count', 1)}")
                
                plan = result["workout_plan"]
                critique = result["critique"]
                
                # Safety Badge
                if critique["status"] == "SAFE":
                    st.markdown('<span class="safe-badge">✅ SAFE - Approved by AI Physiotherapist</span>', 
                               unsafe_allow_html=True)
                else:
                    st.markdown('<span class="unsafe-badge">⚠️ Review Required</span>', 
                               unsafe_allow_html=True)
                
                # Plan Details
                st.subheader(f"📋 {plan['name']}")
                st.write(f"**Frequency:** {plan['frequency']}")
                
                # Exercises Table
                exercises = plan.get("exercises", [])
                if exercises:
                    ex_df = pd.DataFrame(exercises)
                    st.dataframe(ex_df, use_container_width=True, hide_index=True)
                
                # Critique Feedback
                st.subheader("🩺 Safety Review")
                st.write(critique.get("feedback", "No feedback available"))
                
                if critique.get("flagged_exercises"):
                    st.warning(f"Flagged exercises: {', '.join(critique['flagged_exercises'])}")
                
                # Save Plan Button
                if st.button("💾 Save This Plan"):
                    try:
                        client.save_plan({
                            "plan_name": plan['name'],
                            "plan_data": plan,
                            "critique_data": critique,
                            "revision_count": result.get('revision_count', 1),
                            "safety_status": critique["status"],
                            "goals": goals,
                            "total_latency_ms": int(elapsed * 1000)
                        })
                        st.success("✅ Plan saved!")
                    except Exception as e:
                        st.error(f"Failed to save: {e}")
                
            except Exception as e:
                st.error(f"❌ Error generating plan: {e}")
                progress.empty()
                status.empty()


# ============= Injury Profile ============= #

def show_injury_profile():
    """Show injury profile management."""
    st.header("🩹 Injury Profile")
    
    st.markdown("""
    Manage your injury history. Active injuries will be considered when generating workout plans
    to ensure exercises are safe for you.
    """)
    
    # Add new injury
    st.subheader("Add Injury")
    
    with st.form("add_injury"):
        col1, col2 = st.columns(2)
        
        with col1:
            injury_type = st.text_input("Injury Type", placeholder="e.g., Rotator cuff strain")
            injury_date = st.date_input("Injury Date", value=date.today())
        
        with col2:
            severity = st.selectbox("Severity", ["mild", "moderate", "severe"])
            is_active = st.checkbox("Currently affecting training", value=True)
        
        notes = st.text_area("Notes", placeholder="e.g., Avoid overhead movements")
        
        submitted = st.form_submit_button("➕ Add Injury", use_container_width=True)
        
        if submitted and injury_type:
            try:
                client.create_injury({
                    "injury_type": injury_type,
                    "injury_date": str(injury_date),
                    "severity": severity,
                    "is_active": is_active,
                    "notes": notes
                })
                st.success("✅ Injury added!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ {e}")
    
    st.markdown("---")
    
    # Injury list
    st.subheader("Your Injuries")
    
    try:
        injuries = client.get_injuries()
        
        if injuries:
            for inj in injuries:
                with st.expander(f"{'🔴' if inj['is_active'] else '🟢'} {inj['injury_type']} - {inj['severity'].upper()}"):
                    st.write(f"**Date:** {inj['injury_date'][:10]}")
                    st.write(f"**Status:** {'Active' if inj['is_active'] else 'Recovered'}")
                    st.write(f"**Notes:** {inj.get('notes', 'None')}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if inj['is_active']:
                            if st.button(f"✅ Mark as Recovered", key=f"recover_{inj['id']}"):
                                client.update_injury(inj['id'], {"is_active": False})
                                st.rerun()
                        else:
                            if st.button(f"🔴 Mark as Active", key=f"active_{inj['id']}"):
                                client.update_injury(inj['id'], {"is_active": True})
                                st.rerun()
                    with col2:
                        if st.button(f"🗑️ Delete", key=f"delete_{inj['id']}"):
                            client.delete_injury(inj['id'])
                            st.rerun()
        else:
            st.info("No injuries recorded. Add injuries above.")
    except Exception as e:
        st.error(f"Failed to load injuries: {e}")


# ============= Plan History ============= #

def show_plan_history():
    """Show saved workout plans history."""
    st.header("📁 Plan History")
    
    try:
        plans = client.get_plans()
        
        if plans:
            st.markdown(f"**{len(plans)} plans saved**")
            
            for plan in plans:
                status_badge = "🟢" if plan['safety_status'] == 'SAFE' else "🟡"
                with st.expander(f"{status_badge} {plan['plan_name']} - {plan['created_at'][:10]}"):
                    st.write(f"**Safety Status:** {plan['safety_status']}")
                    st.write(f"**Revisions:** {plan['revision_count']}")
                    
                    # Load full plan details
                    if st.button(f"📋 View Full Plan", key=f"view_{plan['id']}"):
                        full_plan = client.get_plan(plan['id'])
                        if full_plan:
                            st.json(full_plan['plan_data'])
                    
                    if st.button(f"🗑️ Delete", key=f"del_plan_{plan['id']}"):
                        client.delete_plan(plan['id'])
                        st.rerun()
        else:
            st.info("No saved plans yet. Generate a plan in the AI Coach section!")
    except Exception as e:
        st.error(f"Failed to load plans: {e}")


# ============= Sidebar ============= #

def show_sidebar():
    """Show sidebar with navigation and settings."""
    with st.sidebar:
        if st.session_state["user"]:
            st.markdown(f"### 👤 {st.session_state['user']['username']}")
            st.markdown(f"*{st.session_state['user']['email']}*")
            
            if st.button("🚪 Logout"):
                st.session_state["token"] = None
                st.session_state["user"] = None
                st.rerun()
            
            st.markdown("---")
        
        # Dark Mode Toggle
        st.session_state["dark_mode"] = st.toggle("🌙 Dark Mode", value=st.session_state["dark_mode"])
        
        st.markdown("---")
        
        # API Health
        try:
            health = client.health_check()
            st.success(f"API: {health['status']}")
            st.caption(f"LLM: {health['llm_provider']}")
        except:
            st.error("API: Disconnected")


# ============= Main App ============= #

def main():
    """Main application."""
    show_sidebar()
    
    # Check authentication
    if not st.session_state["token"]:
        show_auth_page()
        return
    
    # Main navigation tabs
    tabs = st.tabs([
        "🏠 Dashboard",
        "📓 Workout Logs", 
        "📊 Analytics",
        "🧑‍🏫 AI Coach",
        "🩹 Injuries",
        "📁 Plan History"
    ])
    
    with tabs[0]:
        show_dashboard()
    
    with tabs[1]:
        show_workout_logs()
    
    with tabs[2]:
        show_analytics()
    
    with tabs[3]:
        show_ai_coach()
    
    with tabs[4]:
        show_injury_profile()
    
    with tabs[5]:
        show_plan_history()


if __name__ == "__main__":
    main()
