import sqlite3
import json
from typing import Optional

DB_PATH = "trainer.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def _column_type(conn, table: str, col: str) -> Optional[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    for _, name, ctype, *_ in cur.fetchall():
        if name.lower() == col.lower():
            return (ctype or "").upper()
    return None

def _migrate_reps_to_text(conn):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS workouts_new (
        id INTEGER PRIMARY KEY,
        date TEXT NOT NULL,
        exercise TEXT NOT NULL,
        sets INTEGER,
        reps TEXT,
        weight REAL
    )
    """)
    cur.execute("""
    INSERT INTO workouts_new (id, date, exercise, sets, reps, weight)
    SELECT id, date, exercise, sets, CAST(reps AS TEXT), weight FROM workouts
    """)
    cur.execute("DROP TABLE IF EXISTS workouts")
    cur.execute("ALTER TABLE workouts_new RENAME TO workouts")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_workouts_exercise ON workouts(exercise)")
    conn.commit()

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY,
        date TEXT NOT NULL,
        exercise TEXT NOT NULL,
        sets INTEGER,
        reps TEXT,
        weight REAL
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_workouts_exercise ON workouts(exercise)")
    conn.commit()

    ctype = _column_type(conn, "workouts", "reps")
    if ctype and ctype != "TEXT":
        _migrate_reps_to_text(conn)

    conn.close()

def save_workout(entry: dict):
    reps_val = entry.get("reps")
    if isinstance(reps_val, list):
        reps_db = json.dumps(reps_val)
    else:
        reps_db = None if reps_val is None else str(int(reps_val))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO workouts (date, exercise, sets, reps, weight) VALUES (?, ?, ?, ?, ?)",
        (entry.get("date"), entry.get("exercise"), entry.get("sets"), reps_db, entry.get("weight")),
    )
    conn.commit()
    conn.close()

def get_workouts():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, date, exercise, sets, reps, weight FROM workouts ORDER BY date DESC, id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def clear_workouts(exercise: Optional[str] = None):
    conn = get_conn()
    cur = conn.cursor()
    if exercise:
        cur.execute("DELETE FROM workouts WHERE lower(exercise) = lower(?)", (exercise,))
    else:
        cur.execute("DELETE FROM workouts")
    conn.commit()
    conn.close()

def delete_last_entry():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM workouts ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    if row:
        cur.execute("DELETE FROM workouts WHERE id = ?", (row[0],))
        conn.commit()
    conn.close()

def delete_by_id(row_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM workouts WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()
