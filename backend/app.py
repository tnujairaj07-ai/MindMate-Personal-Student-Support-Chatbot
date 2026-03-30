# backend/app.py
import os
import time
import logging
from typing import Optional
from collections import defaultdict
from flask import Flask, render_template, request, jsonify, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from backend.config import Config

from backend.db import (
    get_db,
    close_db,
    get_notices,
    get_deadlines,
    add_deadline,
    get_syllabus,
    get_pyqs,
    get_projects,
    get_helplines,
    add_complaint,
    get_complaints,
    get_complaints_summary,
    get_complaints_by_department,
    get_intent_counts, 
    log_chat_message,
    get_user_by_id,
    get_student_by_email,
    get_student_by_user_id,      
    upsert_student_for_user,    
    get_or_create_user_settings,
    update_user_settings,
    get_deadlines_for_student, 
    get_resources,
    get_resource_by_id,
    create_resource,
    update_resource,
    delete_resource,
    get_saved_resources_for_user,
    save_resource_for_user,
    remove_saved_resource,

)
from backend.chatbot import get_llm_response # now returns (reply, intent, mood)
LOGIN_WINDOW_SECONDS = 60        # time window
LOGIN_MAX_ATTEMPTS = 10          # max attempts per IP per window

_signup_attempts = defaultdict(list)
_login_attempts = defaultdict(list)

def _rate_limited(bucket: dict, key: str) -> bool:
    now = time.time()
    window_start = now - LOGIN_WINDOW_SECONDS
    # keep only recent timestamps
    bucket[key] = [t for t in bucket[key] if t >= window_start]
    if len(bucket[key]) >= LOGIN_MAX_ATTEMPTS:
        return True
    bucket[key].append(now)
    return False

# Create Flask app using central Config
app = Flask(
    __name__,
    template_folder=Config.TEMPLATES_DIR,
    static_folder=Config.STATIC_DIR,
)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY
app.teardown_appcontext(close_db)

DEMO_MODE = Config.DEMO_MODE

# basic logging setup
logging.basicConfig(
    level=logging.INFO if not Config.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------- HELPERS ----------
def create_user(email: str, name: str, role: str, password: str):
    db = get_db()
    hashed = generate_password_hash(password)
    db.execute(
        "INSERT INTO users (email, name, role, password) VALUES (?, ?, ?, ?)",
        (email, name, role, hashed),
    )
    db.commit()

def find_user_by_email(email: str):
    db = get_db()
    cur = db.execute("SELECT * FROM users WHERE email = ?", (email,))
    return cur.fetchone()

def get_or_create_user(email: str, role: str):
    """
    Used only for anonymous fallback in /api/chat.
    In DEMO_MODE, creates a demo user if not exists.
    In non-demo mode, returns None instead of auto-creating users.
    """
    db = get_db()
    cur = db.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    if row:
        return row

    if not DEMO_MODE:
        # In production, do not silently create users
        return None

    name = "Admin User" if role == "admin" else "Student User"
    hashed = generate_password_hash("demo")
    db.execute(
        "INSERT INTO users (email, name, role, password) VALUES (?, ?, ?, ?)",
        (email, name, role, hashed),
    )
    db.commit()
    cur = db.execute("SELECT * FROM users WHERE email = ?", (email,))
    return cur.fetchone()

def save_message(user_id: int, text: str, role: str, intent: Optional[str] = None):
    db = get_db()
    db.execute(
        "INSERT INTO messages (user_id, text, role, intent) VALUES (?, ?, ?, ?)",
        (user_id, text, role, intent),
    )
    db.commit()

def require_admin():
    user_id = session.get("user_id")
    if not user_id:
        abort(401)
    db = get_db()
    cur = db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    if not user or user["role"] != "admin":
        abort(403)
    return user

def require_login():
    user_id = session.get("user_id")
    if not user_id:
        abort(401)
    return user_id

# ---------- AUTH ROUTES ----------
MIN_PASSWORD_LENGTH = 8

def is_password_strong(password: str) -> bool:
    if len(password) < MIN_PASSWORD_LENGTH:
        return False
    has_digit = any(c.isdigit() for c in password)
    has_alpha = any(c.isalpha() for c in password)
    return has_digit and has_alpha

@app.post("/api/signup")
def api_signup():
    client_ip = request.remote_addr or "unknown"
    if _rate_limited(_signup_attempts, client_ip):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Too many signup attempts. Please wait a minute and try again.",
                }
            ),
            429,
        )
    
    data = request.get_json() or {}
    email = (data.get("email") or "").strip()
    name = (data.get("name") or "").strip() or "Student User"
    role = data.get("role") or "student"
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password required"}), 400

    if not is_password_strong(password):
        return (
            jsonify(
                {
                    "success": False,
                    "error": (
                        "Password must be at least 8 characters long and include "
                        "both letters and numbers."
                    ),
                }
            ),
            400,
        )

    if role not in ("student", "admin"):
        role = "student"

    if find_user_by_email(email):
        return jsonify({"success": False, "error": "User already exists"}), 400

    create_user(email, name, role, password)
    user = find_user_by_email(email)
    session["user_id"] = user["id"]

    return jsonify(
        {
            "success": True,
            "role": user["role"],
            "name": user["name"],
            "user_id": user["id"],
        }
    )

@app.post("/api/login")
def api_login():
    client_ip = request.remote_addr or "unknown"
    if _rate_limited(_login_attempts, client_ip):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Too many login attempts. Please wait a minute and try again.",
                }
            ),
            429,
        )
    
    data = request.get_json() or {}
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password required"}), 400

    user = find_user_by_email(email)
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"success": False, "error": "Invalid credentials"}), 401

    session["user_id"] = user["id"]
    session["role"] = user["role"]

    return jsonify(
        {
            "success": True,
            "role": user["role"],
            "name": user["name"],
            "user_id": user["id"],
        }
    )

# ---------- PROFILE ROUTES ----------
@app.get("/api/profile")
def api_get_profile():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify(success=False, error="Not logged in"), 401

    user = get_user_by_id(user_id)
    if not user:
        return jsonify(success=False, error="User not found"), 404

    # try to match with students table by email
    student = get_student_by_user_id(user_id)
    
    profile = {
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "roll_no": student["roll_no"] if student else "",
        "course": student["course"] if student else "",
        "year": student["year"] if student else None,
        "semester": student["semester"] if student and "semester" in student.keys() else None,
    }
    return jsonify(success=True, profile=profile)

@app.put("/api/profile")
def api_update_profile():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify(success=False, error="Not logged in"), 401

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    roll_no = (data.get("roll_no") or "").strip()
    course = (data.get("course") or "").strip()
    year = data.get("year")
    semester = data.get("semester")

    # parse ints safely
    try:
        year = int(year) if year not in (None, "") else None
    except ValueError:
        year = None
    try:
        semester = int(semester) if semester not in (None, "") else None
    except ValueError:
        semester = None

    db = get_db()

    # update users.name if provided
    if name:
        db.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
        db.commit()

    # fetch updated user to get email + final name
    user = get_user_by_id(user_id)
    if not user:
        return jsonify(success=False, error="User not found"), 404

    final_name = name or user["name"]
    email = user["email"]

    # Use helper to upsert into students table (Phase 3)
    upsert_student_for_user(
        user_id=user_id,
        name=final_name,
        email=email,
        roll_no=roll_no or None,
        course=course or None,
        year=year,
        semester=semester,
    )

    return jsonify(success=True)

# ---------- SETTINGS ROUTES ----------
@app.get("/api/settings")
def api_get_settings():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify(success=False, error="Not logged in"), 401

    row = get_or_create_user_settings(user_id)
    settings = {
        "theme": row["theme"],
        "preferred_language": row["preferred_language"],
        "chat_mode": row["chat_mode"],
        "allow_analytics": bool(row["allow_analytics"]),
        "show_deadlines_card": bool(row["show_deadlines_card"]),
        "show_notices_card": bool(row["show_notices_card"]),
    }
    return jsonify(success=True, settings=settings)

@app.put("/api/settings")
def api_update_settings():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify(success=False, error="Not logged in"), 401

    data = request.get_json() or {}
    theme = (data.get("theme") or "dark").strip()
    preferred_language = (data.get("preferred_language") or "auto").strip()
    chat_mode = (data.get("chat_mode") or "auto").strip()

    allow_analytics = 1 if data.get("allow_analytics", True) else 0
    show_deadlines_card = 1 if data.get("show_deadlines_card", True) else 0
    show_notices_card = 1 if data.get("show_notices_card", True) else 0

    update_user_settings(
        user_id,
        theme,
        preferred_language,
        chat_mode,
        allow_analytics,
        show_deadlines_card,
        show_notices_card,
    )
    return jsonify(success=True)

# ---------- MAIN ROUTES ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.post("/api/chat")
def api_chat():
    data = request.get_json() or {}
    message = (data.get("message") or "").strip()
    user_id = data.get("user_id") or session.get("user_id")
    mode = (data.get("mode") or "auto").strip()

    if not message:
        return (
            jsonify(success=False, error="Please type something so I can help."),
            400,
        )

    # Ensure we have a user (or anonymous demo user)
    if not user_id:
        if DEMO_MODE:
            user = get_or_create_user("anonymous@student.local", "student")
            if user:
                user_id = user["id"]
        else:
            return (
                jsonify(success=False, error="Please log in first to chat."),
                401,
            )

    try:
        # TEMP: force an error here for testing
        # (uncomment this line when you want to test logging)
        # raise RuntimeError("Intentional test error in /api/chat")

        # Save user message (linked to user)
        if user_id:
            save_message(user_id, message, "user", None)

        # Get reply, intent, mood from chatbot
        reply, intent, mood = get_llm_response(message, mode=mode)

        # Save bot reply with intent
        if user_id:
            save_message(user_id, reply, "bot", intent)

        # Also log to chat_messages (session-based, anonymised)
        session_id = request.cookies.get("session_id") or "anonymous-session"
        log_chat_message(session_id, "user", message, intent_detected=None)
        log_chat_message(session_id, "bot", reply, intent_detected=intent)

        # Return all three values to frontend
        return jsonify(
            success=True,
            reply=reply,
            intent=intent,
            mood=mood,
        )

    except Exception:
        logger.exception("Error in /api/chat")
        return (
            jsonify(
                success=False,
                error=(
                    "Sorry, something went wrong while processing your message. "
                    "Please try again."
                ),
            ),
            500,
        )

@app.post("/api/studyplan")
def api_studyplan():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify(success=False, error="Not logged in"), 401

    data = request.get_json() or {}
    subject = (data.get("subject") or "").strip()
    hours_per_day = data.get("hours_per_day") or 2

     # Get student info
    student = get_student_by_user_id(user_id)
    course = student["course"] if student else None
    year = student["year"] if student else None

    # reuse deadlines helper
    try:
        if course:
            dl_rows = get_deadlines_for_student(course, limit=None)
        else:
            dl_rows = get_deadlines()
    except Exception:
        dl_rows = []

    subject_deadlines = [
        dict(r)
        for r in dl_rows
        if subject and r["subject"] and r["subject"].lower() == subject.lower()
    ]

    context_lines = []
    if student:
        context_lines.append(
            f"Student course: {course or 'Unknown'}, year: {year or 'Unknown'}."
        )
    if subject:
        context_lines.append(f"Subject: {subject}.")
    if subject_deadlines:
        dl_str = "; ".join(
            f"{d['label']} on {d['due_date']}" for d in subject_deadlines
        )
        context_lines.append(f"Upcoming deadlines: {dl_str}.")
    else:
        context_lines.append("No specific deadlines found for this subject.")

    system_msg = (
        "You are a helpful academic coach. "
        "Create a realistic 5–7 bullet study plan tailored to the student's context. "
        "Keep each bullet short and actionable."
        "Emphasize balance and stress management."
    )
    user_msg = (
        "\n".join(context_lines)
        + f"\nThe student can study about {hours_per_day} hours per day."
    )

    # use your existing chatbot backend; here we reuse get_llm_response
    try:
        # We give combined prompt to get_llm_response; you can extend its signature if needed
        reply, intent, mood = get_llm_response(
            f"STUDY_PLAN_REQUEST:\n{user_msg}",
            mode="academics",
        )
        return jsonify(success=True, plan=reply, intent=intent, mood=mood)
    except Exception:
        logger.exception("Error in /api/studyplan:")
        return jsonify(success=False, error="Failed to generate study plan"), 500

# ---------- SIMPLE NOTICES (right panel) ----------
@app.get("/api/notices")
def api_notices():
    rows = get_notices()
    items = [
        {
            "title": r["title"],
            "description": r["description"],
        }
        for r in rows[:5]
    ]
    return jsonify({"items": items})

@app.get("/api/deadlines")
def api_deadlines():
    user_id = session.get("user_id")
    course = None

    if user_id:
        student = get_student_by_user_id(user_id)
        if student:
            course = student["course"]

    if course:
        rows = get_deadlines_for_student(course, limit=None)
    else:
        rows = get_deadlines()

    items = [
        {
            "id": r["id"],
            "label": r["label"],
            "due_date": r["due_date"],
            "course": r["course"],
            "subject": r["subject"],
            "type": r["type"],
        }
        for r in rows
    ]
    return jsonify(items=items)

@app.post("/api/deadlines")
def api_create_deadline():
    # restrict to admin
    role = session.get("role")
    if role != "admin":
        return jsonify(success=False, error="Not authorized"), 403

    data = request.get_json() or {}
    label = (data.get("label") or "").strip()
    due_date = (data.get("due_date") or "").strip()  # expected format: YYYY-MM-DD
    course = (data.get("course") or "").strip()
    subject = (data.get("subject") or "").strip()
    type_ = (data.get("type") or "").strip() or "assignment"
    visible_to = (data.get("visible_to") or "").strip() or "student"

    if not label or not due_date:
        return jsonify(success=False, error="Label and due date are required"), 400

    try:
        add_deadline(label, due_date, course, subject, type_, visible_to)
        return jsonify(success=True)
    except Exception:
        logger.exception("Error adding deadline:")
        return jsonify(success=False, error="Failed to add deadline"), 500
    

# ---------- ACADEMIC DATA APIs (team DB integrated) ----------
@app.get("/api/academic/notices")
def api_academic_notices():
    try:
        rows = get_notices()
        items = [
            {"title": r["title"], "description": r["description"]}
            for r in rows
        ]
        return jsonify({"items": items})
    except Exception:
        logger.exception("Error in /api/academic/notices:")
        return jsonify({"items": []}), 500

@app.get("/api/academic/syllabus")
def api_academic_syllabus():
    subject = (request.args.get("subject") or "").strip()
    course = (request.args.get("course") or "").strip()

    if not subject:
        return jsonify({"items": []})

    # infer course from logged‑in student if not provided
    if not course:
        user_id = session.get("user_id")
        if user_id:
            student = get_student_by_user_id(user_id)
            if student and student["course"]:
                course = student["course"]

    try:
       # For now, get_syllabus ignores course; later you can create get_syllabus_for_course()
        rows = get_syllabus(subject)
        items = [{"unit": r["unit"], "topics": r["topics"]} for r in rows]
        return jsonify({"items": items})
    except Exception:
        logger.exception("Error in /api/academic/syllabus:")
        return jsonify({"items": []}), 500

@app.get("/api/academic/pyqs")
def api_academic_pyqs():
    subject = (request.args.get("subject") or "").strip()
    course = (request.args.get("course") or "").strip()

    if not subject:
        return jsonify({"items": []})

    if not course:
        user_id = session.get("user_id")
        if user_id:
            student = get_student_by_user_id(user_id)
            if student and student["course"]:
                course = student["course"]

    try:
        rows = get_pyqs(subject)
        items = [{"year": r["year"], "question": r["question"]} for r in rows]
        return jsonify({"items": items})
    except Exception:
        logger.exception("Error in /api/academic/pyqs:")
        return jsonify({"items": []}), 500

@app.get("/api/academic/projects")
def api_academic_projects():
    try:
        rows = get_projects()
        items = [
            {
                "title": r["title"],
                "domain": r["domain"],
                "description": r["description"],
                "difficulty": r["difficulty"],
            }
            for r in rows
        ]
        return jsonify({"items": items})
    except Exception:
        logger.exception("Error in /api/academic/projects:")
        return jsonify({"items": []}), 500

@app.get("/api/academic/helplines")
def api_academic_helplines():
    try:
        rows = get_helplines()
        items = [
            {
                "name": r["name"],
                "phone": r["phone"],
                "email": r["email"],
                "available_hours": r["available_hours"],
                "type": r["type"],
            }
            for r in rows
        ]
        return jsonify({"items": items})
    except Exception:
        logger.exception("Error in /api/academic/helplines:")
        return jsonify({"items": []}), 500
    

# ---------- ADMIN: notice CRUD ----------
@app.route("/api/admin/notices", methods=["GET"])
def admin_list_notices():
    require_admin()
    rows = get_notices()
    items = [dict(r) for r in rows] if rows else []
    return jsonify({"success": True, "items": items})

@app.route("/api/admin/notices", methods=["POST"])
def admin_create_notice():
    require_admin()  # we don't actually need the admin object here
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    if not title:
        return jsonify({"success": False, "error": "Title is required"}), 400

    category = (data.get("category") or "").strip() or "general"
    visible_to = (data.get("visible_to") or "").strip() or "student"

    db = get_db()
    cur = db.execute(
        """
        INSERT INTO notices (title, description, category, date_posted, visible_to)
        VALUES (?, ?, ?, DATE('now'), ?)
        """,
        (title, description, category, visible_to),
    )
    db.commit()
    return jsonify({"success": True, "id": cur.lastrowid})

@app.route("/api/admin/notices/<int:notice_id>", methods=["PUT"])
def admin_update_notice(notice_id):
    require_admin()
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    if not title:
        return jsonify({"success": False, "error": "Title is required"}), 400
    db = get_db()
    db.execute(
        "UPDATE notices SET title = ?, description = ? WHERE notice_id = ?",
        (title, description, notice_id),
    )
    db.commit()
    return jsonify({"success": True})

@app.route("/api/admin/notices/<int:notice_id>", methods=["DELETE"])
def admin_delete_notice(notice_id):
    require_admin()
    db = get_db()
    db.execute("DELETE FROM notices WHERE notice_id = ?", (notice_id,))
    db.commit()
    return jsonify({"success": True})


# ---------- ADMIN: Resources CRUD ----------
@app.route("/api/resources", methods=["GET"])
def list_resources():
    subject = request.args.get("subject")
    items = get_resources(subject)
    return jsonify({"success": True, "items": items})

@app.route("/api/admin/resources", methods=["GET"])
def admin_list_resources():
    require_admin()
    items = get_resources()
    return jsonify({"success": True, "items": items})

@app.route("/api/admin/resources", methods=["POST"])
def admin_create_resource():
    require_admin()
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    type_ = data.get("type", "").strip() or "link"
    subject = data.get("subject")
    semester = data.get("semester")
    program = data.get("program")
    url = data.get("url")
    description = data.get("description")
    visible_to = data.get("visible_to", "student")
    if not title:
        return jsonify({"success": False, "error": "Title is required"}), 400
    new_id = create_resource(
        title, type_, subject, semester, program, url, description, visible_to
    )
    return jsonify({"success": True, "id": new_id})

@app.route("/api/admin/resources/<int:resource_id>", methods=["PUT"])
def admin_update_resource(resource_id):
    require_admin()
    data = request.get_json() or {}
    # Fetch existing to allow partial updates
    existing = get_resource_by_id(resource_id)
    if not existing:
        return jsonify({"success": False, "error": "Resource not found"}), 404
    title = data.get("title", existing["title"]).strip()
    type_ = data.get("type", existing["type"]).strip()
    subject = data.get("subject", existing["subject"])
    semester = data.get("semester", existing["semester"])
    program = data.get("program", existing["program"])
    url = data.get("url", existing["url"])
    description = data.get("description", existing["description"])
    visible_to = data.get("visible_to", existing["visible_to"])
    update_resource(resource_id, title, type_, subject, semester, program, url, description, visible_to)
    return jsonify({"success": True})

@app.route("/api/admin/resources/<int:resource_id>", methods=["DELETE"])
def admin_delete_resource(resource_id):
    require_admin()
    delete_resource(resource_id)
    return jsonify({"success": True})


# ---------- Saved resources APIs ----------
@app.route("/api/resources/saved", methods=["GET"])
def get_saved_resources():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "Not logged in"}), 401
    items = get_saved_resources_for_user(user_id)
    return jsonify({"success": True, "items": items})

@app.route("/api/resources/saved", methods=["POST"])
def add_saved_resource():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "Not logged in"}), 401
    data = request.get_json() or {}
    resource_id = data.get("resource_id")
    if not resource_id:
        return jsonify({"success": False, "error": "resource_id is required"}), 400
    save_resource_for_user(user_id, resource_id)
    return jsonify({"success": True})

@app.route("/api/resources/saved/<int:saved_id>", methods=["DELETE"])
def delete_saved_resource(saved_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "Not logged in"}), 401
    remove_saved_resource(saved_id, user_id)
    return jsonify({"success": True})

# ---------- ADMIN: COMPLAINTS & SUMMARY ----------
@app.get("/api/admin/complaints")
def api_admin_complaints():
    require_admin()
    try:
        rows = get_complaints()
        items = [dict(r) for r in rows] if rows and not isinstance(rows[0], dict) else rows
        return jsonify({"items": items})
    except Exception:
        logger.exception("Error in /api/admin/complaints:")
        return jsonify({"items": []}), 500

@app.get("/api/admin/complaints/summary")
def api_admin_complaints_summary():
    require_admin()
    try:
        rows = get_complaints_summary()
        items = [dict(r) for r in rows] if rows and not isinstance(rows[0], dict) else rows
        return jsonify({"items": items})
    except Exception:
        logger.exception("Error in /api/admin/complaints/summary:")
        return jsonify({"items": []}), 500
    
@app.post("/api/complaints")
def api_submit_complaint():
    data = request.get_json() or {}
    studentname = (data.get("studentname") or "").strip()
    rollno = (data.get("rollno") or "").strip()
    department = (data.get("department") or "").strip()
    complainttext = (data.get("complainttext") or "").strip()

    if not complainttext:
        return jsonify(success=False, error="Complaint text is required"), 400

    try:
        add_complaint(studentname or "Anonymous", rollno or "", department or "", complainttext)
        return jsonify(success=True)
    except Exception:
        logger.exception("Error saving complaint:")
        return jsonify(success=False, error="Failed to save complaint"), 500
    
# ---------- INSIGHTS ----------
@app.get("/api/insights/overview")
def api_insights_overview():
    # Complaints grouped by department
    comp_rows = get_complaints_by_department()
    complaints_by_dept = [
        {"department": r["department"] or "Unknown", "count": r["count"]}
        for r in comp_rows
    ]

    # Top intents from messages
    intent_rows = get_intent_counts()
    intents = [
        {"intent": r["intent"] or "unknown", "count": r["count"]}
        for r in intent_rows
    ]

    return jsonify(
        complaints_by_department=complaints_by_dept,
        intents=intents,
    )

if __name__ == "__main__":
    app.run(debug=True)