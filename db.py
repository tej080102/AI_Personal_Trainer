import sqlite3
import json
import hashlib
from pathlib import Path

DB_FILE = Path(__file__).parent / "trainer.db"


def init_db():
    """Initialize the database with cardio fields and user table."""
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()

        # --- Workouts table ---
        cur.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY,
            user_id TEXT NOT NULL,
            date TEXT NOT NULL,
            exercise TEXT NOT NULL,
            sets INTEGER,
            reps TEXT,
            weight REAL,
            distance REAL,
            duration REAL
        )
        """)

        # --- Users table ---
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
        """)

        conn.commit()


# -------- User management -------- #
def create_user(username, password):
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO users (username, password_hash) VALUES (?, ?)", (username, pw_hash))
        conn.commit()


def check_user(username, password):
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        return row and row[0] == pw_hash


# -------- Workout management -------- #
def save_workout(entry):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        reps_db = None
        if entry.get("reps") is not None:
            try:
                reps_db = json.dumps(entry["reps"])
            except Exception:
                reps_db = str(entry["reps"])
        cur.execute(
            """
            INSERT INTO workouts (user_id, date, exercise, sets, reps, weight, distance, duration)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.get("user_id"),
                entry.get("date"),
                entry.get("exercise"),
                entry.get("sets"),
                reps_db,
                entry.get("weight"),
                entry.get("distance"),
                entry.get("duration"),
            ),
        )
        conn.commit()


def get_workouts(user_id):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, date, exercise, sets, reps, weight, distance, duration
            FROM workouts
            WHERE user_id=?
            ORDER BY date DESC, id DESC
        """, (user_id,))
        rows = cur.fetchall()
        result = []
        for row in rows:
            row = list(row)
            try:
                row[4] = json.loads(row[4]) if row[4] else None
            except Exception:
                pass
            result.append(row)
        return result


def clear_workouts(exercise=None, user_id=None):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        if exercise:
            cur.execute("DELETE FROM workouts WHERE user_id=? AND lower(exercise)=?", (user_id, exercise.lower()))
        else:
            cur.execute("DELETE FROM workouts WHERE user_id=?", (user_id,))
        conn.commit()


def delete_last_entry(user_id):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM workouts WHERE id = (SELECT id FROM workouts WHERE user_id=? ORDER BY id DESC LIMIT 1)", (user_id,))
        conn.commit()


def delete_by_id(entry_id, user_id):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM workouts WHERE id=? AND user_id=?", (entry_id, user_id))
        conn.commit()
