# backend/chatbot.py

from backend.llm_ollama import chat_with_ollama
from backend.db import get_notices_dict, get_syllabus, get_pyqs, get_projects, get_helplines

SYSTEM_PROMPT = """
You are MindMate, a friendly and empathetic campus companion for college students.
Your goals:
- Listen carefully to the student's feelings about exams, projects, friends, and campus life.
- Respond in short, clear paragraphs.
- Be encouraging and non-judgmental.
- If the student sounds in serious danger or crisis, gently suggest they talk to a trusted person
  or a professional helpline.
"""

# ---------- Keyword maps for intents and mood ----------

ACADEMIC_KEYWORDS = {
    "notices": ["notice", "notices", "announcement", "announcements", "circular", "update", "news"],
    "syllabus": ["syllabus", "course outline", "course content", "topics", "chapters"],
    "pyqs": ["pyq", "pyqs", "previous year", "past paper", "old paper", "question paper"],
    "projects": ["project", "projects", "project idea", "project ideas", "mini project"],
    "helplines": ["helpline", "helplines", "counselor", "counselling", "counseling", "therapy"],
}

NEGATIVE_KEYWORDS = [
    "stressed", "stress", "anxious", "anxiety", "overwhelmed",
    "sad", "depressed", "depression", "hopeless", "tired",
    "burnt out", "burnout", "worried", "nervous", "scared",
    "lonely", "alone", "crying", "cry",
]

CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "self harm", "self-harm",
    "cut myself", "jump off", "no reason to live", "life is pointless",
]

EXAM_STRESS_KEYWORDS = [
    "exam", "exams", "mid sem", "midsem", "test", "tests",
    "paper", "papers", "marks", "result", "results",
    "backlog", "supply", "supplementary",
]

def detect_intent_and_mood(user_text: str) -> tuple[str, str]:
    """
    Very simple keyword-based intent + mood detector.
    Returns (intent, mood_tag).
      - intent: 'notices', 'syllabus', 'pyqs', 'projects', 'helplines',
                'exam_stress', 'wellbeing', or 'general'
      - mood_tag: 'crisis_risk', 'negative', or 'neutral'
    """
    text = user_text.lower()

    # Mood detection
    mood = "neutral"
    if any(kw in text for kw in CRISIS_KEYWORDS):
        mood = "crisis_risk"
    elif any(kw in text for kw in NEGATIVE_KEYWORDS):
        mood = "negative"

    # Academic intents
    for intent_name, keywords in ACADEMIC_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return intent_name, mood

    # Exam stress intent
    if any(kw in text for kw in EXAM_STRESS_KEYWORDS):
        return "exam_stress", mood

    # Wellbeing / feelings
    if any(kw in text for kw in ["feel", "feeling", "mental", "mind", "mood", "low", "down"]):
        return "wellbeing", mood

    return "general", mood

def rule_based_academics_reply(user_text: str) -> tuple[str | None, str | None]:
    """
    Returns (reply_text, intent) for academic / utility queries.
    If no rule applies, returns (None, None).
    """
    text = user_text.lower()

    # ----- Notices -----
    if any(kw in text for kw in ACADEMIC_KEYWORDS["notices"]):
        notices = get_notices_dict()
        if not notices:
            return "Right now I don't see any notices in the system.", "notices"
        reply_lines = ["Here are some recent notices:"]
        for n in notices:
            reply_lines.append(f"- {n['title']}: {n['description']}")
        return "\n".join(reply_lines), "notices"

    # ----- Syllabus (simple subject detection) -----
    if any(kw in text for kw in ACADEMIC_KEYWORDS["syllabus"]):
        subject = None
        if "dbms" in text:
            subject = "DBMS"
        elif "os" in text or "operating system" in text:
            subject = "OS"

        if not subject:
            return "Please tell me which subject's syllabus you want, for example DBMS or OS.", "syllabus"

        rows = get_syllabus(subject)
        if not rows:
            return f"I couldn't find a saved syllabus for {subject} yet.", "syllabus"

        reply_lines = [f"Syllabus for {subject}:"]
        for r in rows:
            reply_lines.append(f"- {r['unit']}: {r['topics']}")
        return "\n".join(reply_lines), "syllabus"

    # ----- PYQs -----
    if any(kw in text for kw in ACADEMIC_KEYWORDS["pyqs"]):
        subject = None
        if "dbms" in text:
            subject = "DBMS"
        elif "os" in text or "operating system" in text:
            subject = "OS"

        if not subject:
            return "Please tell me which subject's PYQs you want, for example 'DBMS PYQs'.", "pyqs"

        rows = get_pyqs(subject)
        if not rows:
            return f"I couldn't find PYQs stored for {subject} yet.", "pyqs"

        reply_lines = [f"Some {subject} PYQs:"]
        for r in rows:
            reply_lines.append(f"- {r['year']}: {r['question']}")
        return "\n".join(reply_lines), "pyqs"

    # ----- Projects -----
    if any(kw in text for kw in ACADEMIC_KEYWORDS["projects"]):
        rows = get_projects()
        if not rows:
            return "I don't see any projects saved yet.", "projects"

        reply_lines = ["Here are some project ideas:"]
        for r in rows:
            reply_lines.append(f"- {r['title']} ({r['domain']}, {r['difficulty']}): {r['description']}")
        return "\n".join(reply_lines), "projects"

    # ----- Helplines -----
    if any(kw in text for kw in ACADEMIC_KEYWORDS["helplines"]):
        rows = get_helplines()
        if not rows:
            return (
                "I don't have helplines stored yet, but you can reach out to a trusted person or a "
                "professional counsellor in your college.",
                "helplines",
            )

        reply_lines = ["Here are some mental health helplines you can contact:"]
        for r in rows:
            reply_lines.append(f"- {r['name']} ({r['availablehours']}): {r['phone']}")
        reply_lines.append(
            "If you feel in serious danger, please contact emergency services or a trusted person immediately."
        )
        return "\n".join(reply_lines), "helplines"

    return None, None

def get_llm_response(user_text: str) -> tuple[str, str, str]:
    """
    Main entry for the backend.
    Returns (reply_text, intent, mood_tag).
    """
    if not user_text.strip():
        return "Please type something so I can help.", "general", "neutral"

    # Detect intent + mood
    intent, mood = detect_intent_and_mood(user_text)

    # Try rule-based academic / utility reply first
    rb_reply, rb_intent = rule_based_academics_reply(user_text)
    if rb_reply:
        # If rule-based hit, prefer its specific intent, but keep mood.
        return rb_reply, (rb_intent or intent), mood

    # Otherwise, fall back to LLM
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]

    try:
        reply = chat_with_ollama(messages).strip()
    except Exception as e:
        print("LLM error:", e)
        reply = "Sorry, I had trouble generating a response just now. Please try again in a moment."

    return reply, intent, mood
