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
        """
        SELECT
            notice_id AS id,
            title,
            description,
            category,
            date_posted,
            visible_to
        FROM notices
        ORDER BY date_posted DESC
        """
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

def get_deadlines_for_student(course: str | None, limit: int | None = None):
    db = get_db()
    sql = """
        SELECT id, label, due_date, course, subject, type, visible_to
        FROM deadlines
        WHERE date(due_date) >= date('now')
          AND (visible_to IS NULL OR visible_to IN ('student', 'both'))
    """
    params = []

    if course:
        sql += " AND (course IS NULL OR course = '' OR course = ?)"
        params.append(course)

    sql += " ORDER BY due_date ASC"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)

    return db.execute(sql, tuple(params)).fetchall()

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

def get_user_by_id(user_id: int):
    db = get_db()
    cur = db.execute(
        "SELECT id, email, name, role FROM users WHERE id = ?",
        (user_id,),
    )
    return cur.fetchone()

def get_student_by_email(email: str):
    db = get_db()
    cur = db.execute(
        "SELECT student_id, name, email, roll_no, course, year FROM students WHERE email = ?",
        (email,),
    )
    return cur.fetchone()

def get_student_by_user_id(user_id: int):
    db = get_db()
    row = db.execute(
        """
        SELECT student_id, user_id, name, email, roll_no, course, year, semester
        FROM students
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    return row

def upsert_student_for_user(user_id: int, name: str, email: str | None,
                            roll_no: str | None, course: str | None,
                            year: int | None, semester: int | None):
    db = get_db()
    existing = db.execute(
        "SELECT student_id FROM students WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if existing:
        db.execute(
            """
            UPDATE students
            SET name = ?, email = ?, roll_no = ?, course = ?, year = ?, semester = ?
            WHERE user_id = ?
            """,
            (name, email, roll_no, course, year, semester, user_id),
        )
    else:
        db.execute(
            """
            INSERT INTO students (user_id, name, email, roll_no, course, year, semester)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, name, email, roll_no, course, year, semester),
        )
    db.commit()

def get_or_create_user_settings(user_id: int):
    db = get_db()
    cur = db.execute(
        "SELECT * FROM user_settings WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    if row:
        return row
    db.execute("INSERT INTO user_settings (user_id) VALUES (?)", (user_id,))
    db.commit()
    cur = db.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
    return cur.fetchone()

def update_user_settings(
    user_id: int,
    theme: str,
    preferred_language: str,
    chat_mode: str,
    allow_analytics: int,
    show_deadlines_card: int,
    show_notices_card: int,
):
    db = get_db()
    db.execute(
        """
        UPDATE user_settings
        SET theme = ?,
            preferred_language = ?,
            chat_mode = ?,
            allow_analytics = ?,
            show_deadlines_card = ?,
            show_notices_card = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
        """,
        (
            theme,
            preferred_language,
            chat_mode,
            allow_analytics,
            show_deadlines_card,
            show_notices_card,
            user_id,
        ),
    )
    db.commit()

def get_syllabus_for_course_subject(course: str, subject: str):
    db = get_db()
    rows = db.execute(
        "SELECT unit, topics FROM syllabus WHERE subject = ? AND (course = ? OR course IS NULL)",
        (subject, course),
    ).fetchall()
    return rows

# ----------Resources----------------------
def get_resources(subject: str | None = None):
    db = get_db()
    if subject:
        rows = db.execute(
            "SELECT * FROM resources WHERE subject = ? ORDER BY created_at DESC",
            (subject,),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM resources ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]

def get_resource_by_id(resource_id: int):
    db = get_db()
    row = db.execute(
        "SELECT * FROM resources WHERE id = ?",
        (resource_id,),
    ).fetchone()
    return dict(row) if row else None

def create_resource(title, type_, subject, semester, program, url, description, visible_to):
    db = get_db()
    cur = db.execute(
        """
        INSERT INTO resources (title, type, subject, semester, program, url, description, visible_to)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (title, type_, subject, semester, program, url, description, visible_to),
    )
    db.commit()
    return cur.lastrowid

def update_resource(resource_id, title, type_, subject, semester, program, url, description, visible_to):
    db = get_db()
    db.execute(
        """
        UPDATE resources
        SET title = ?, type = ?, subject = ?, semester = ?, program = ?, url = ?, description = ?, updated_at = CURRENT_TIMESTAMP, visible_to = ?
        WHERE id = ?
        """,
        (title, type_, subject, semester, program, url, description, visible_to, resource_id),
    )
    db.commit()

def delete_resource(resource_id: int):
    db = get_db()
    db.execute("DELETE FROM resources WHERE id = ?", (resource_id,))
    db.commit()

#------------ Saved resources------------------
def get_saved_resources_for_user(user_id: int):
    db = get_db()
    rows = db.execute(
        """
        SELECT
            id,            -- this is saved_resource id
            resource_id,   -- original resource id (may be NULL later)
            title,
            type,
            subject,
            semester,
            program,
            url,
            description,
            saved_at
        FROM saved_resources
        WHERE user_id = ?
        ORDER BY saved_at DESC
        """,
        (user_id,),
    ).fetchall()
    return [dict(row) for row in rows]

def save_resource_for_user(user_id: int, resource_id: int):
    db = get_db()
    # Fetch the resource to snapshot
    res = db.execute(
        "SELECT * FROM resources WHERE id = ?",
        (resource_id,),
    ).fetchone()
    if not res:
        return

    db.execute(
        """
        INSERT INTO saved_resources (
            user_id, resource_id, title, type, subject,
            semester, program, url, description
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            resource_id,
            res["title"],
            res["type"],
            res["subject"],
            res["semester"],
            res["program"],
            res["url"],
            res["description"],
        ),
    )
    db.commit()

def remove_saved_resource(saved_id: int, user_id: int):
    db = get_db()
    db.execute(
        "DELETE FROM saved_resources WHERE id = ? AND user_id = ?",
        (saved_id, user_id),
        )
    db.commit()