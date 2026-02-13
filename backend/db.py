import sqlite3
import os
from flask import g

DATABASE = "chatbot.db"

def get_db():
    if "db" not in g:
        need_init = not os.path.exists(DATABASE)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row

        if need_init:
            schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
            with open(schema_path, "r", encoding="utf-8") as f:
                g.db.executescript(f.read())
            g.db.commit()
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

# ---------- Team-style helpers on top of get_db ----------

def get_notices():
    db = get_db()
    rows = db.execute(
        "SELECT title, description FROM notices"
    ).fetchall()
    return rows

def get_notices_dict():
    rows = get_notices()
    notices = []
    for row in rows:
        notices.append({
            "title": row["title"],
            "description": row["description"]
        })
    return notices

def get_deadlines(limit: int = 5):
    db = get_db()
    rows = db.execute(
        """
        SELECT id, label, due_date, course, subject, type
        FROM deadlines
        WHERE date(due_date) >= date('now')
        ORDER BY due_date ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return rows

def add_deadline(label, due_date, course, subject, type_, visible_to="student"):
    db = get_db()
    db.execute(
        """
        INSERT INTO deadlines (label, due_date, course, subject, type, visible_to)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (label, due_date, course, subject, type_, visible_to),
    )
    db.commit()

def get_syllabus(subject):
    db = get_db()
    rows = db.execute(
        "SELECT unit, topics FROM syllabus WHERE subject = ?",
        (subject,)
    ).fetchall()
    return rows

def get_pyqs(subject):
    db = get_db()
    rows = db.execute(
        "SELECT year, question FROM pyqs WHERE subject = ?",
        (subject,)
    ).fetchall()
    return rows

def get_projects():
    db = get_db()
    rows = db.execute(
        "SELECT title, description, domain, difficulty FROM projects"
    ).fetchall()
    return rows

def get_helplines():
    db = get_db()
    rows = db.execute(
        "SELECT name, phone, available_hours, email, type FROM helplines"
    ).fetchall()
    return rows

def add_complaint(student_name, roll_no, department, complaint_text):
    db = get_db()
    db.execute(
        """
        INSERT INTO complaints (student_name, roll_no, department, complaint_text)
        VALUES (?, ?, ?, ?)
        """,
        (student_name, roll_no, department, complaint_text),
    )
    db.commit()

def get_complaints():
    db = get_db()
    rows = db.execute(
        """
        SELECT student_name, roll_no, department,
               complaint_text, status, created_at
        FROM complaints
        ORDER BY created_at DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]

def get_complaints_summary():
    """
    Return counts of complaints grouped by department and status.
    """
    db = get_db()
    rows = db.execute(
        """
        SELECT department, status, COUNT(*) as count
        FROM complaints
        GROUP BY department, status
        ORDER BY department, status
        """
    ).fetchall()
    return [dict(row) for row in rows]

def get_complaints_by_department():
    db = get_db()
    rows = db.execute(
        """
        SELECT department, COUNT(*) as count
        FROM complaints
        GROUP BY department
        ORDER BY count DESC
        """
    ).fetchall()
    return rows

def get_intent_counts(limit: int = 5):
    db = get_db()
    rows = db.execute(
        """
        SELECT intent, COUNT(*) as count
        FROM messages
        WHERE intent IS NOT NULL AND intent != ''
        GROUP BY intent
        ORDER BY count DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return rows

def log_chat_message(session_id: str, sender: str, message_text: str, intent_detected: str | None = None):
    """
    Store a privacy-safe chat log entry.
    session_id: anonymised or per-device/session id (not direct user id).
    sender: 'user' or 'bot'.
    """
    db = get_db()
    db.execute(
        """
        INSERT INTO chat_messages (session_id, sender, message_text, intent_detected)
        VALUES (?, ?, ?, ?)
        """,
        (session_id, sender, message_text, intent_detected),
    )
    db.commit()
