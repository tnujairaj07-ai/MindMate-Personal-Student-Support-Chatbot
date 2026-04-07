# backend/chatbot.py
import logging
from typing import List, Dict, Tuple, Optional

from backend.llm_ollama import chat_with_ollama
from backend.db import get_notices_dict, get_syllabus, get_pyqs, get_projects, get_helplines

logger = logging.getLogger(__name__)
SYSTEM_PROMPT = """
You are MindMate, a friendly and empathetic campus companion for college students.
Your goals:
- Listen carefully to the student's feelings about exams, projects, friends, and campus life.
- Respond in short, clear paragraphs.
- Be encouraging and non-judgmental.
- If the student sounds in serious danger or crisis, gently suggest they talk to a trusted person
  or a professional helpline.
"""

INTENT_LABELS = [
    "notices",
    "syllabus",
    "pyqs",
    "projects",
    "helplines",
    "exam_stress",
    "wellbeing",
    "general",
]

MOOD_LABELS = [
    "crisis_risk",
    "negative",
    "neutral",
    "positive",
]


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
    "suicide", "suicidal", "kill myself", "end my life", "self harm", "self-harm",
    "cut myself", "jump off", "no reason to live", "life is pointless",
    "harm myself", "cut myself", "cutting myself", "life is pointless", "life is not worth",
    "end my life", "ending my life", "end it all", "don't want to live", 
    "dont want to live", "no reason to live", "no point in living",
    "kill myself", "harm myself", "i want to die", "i wanna die",
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
    elif any(kw in text for kw in CRISIS_KEYWORDS):
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

DEBUG_CLASSIFIER = False  # set True only when you want to test the LLM classifier

def classify_intent_and_mood(user_text: str) -> Tuple[str, str]:
    """
    Hybrid classifier:
    1) Use fast keyword rules.
    2) Optionally (debug) ask the LLM classifier.
    """
    intent, mood = detect_intent_and_mood(user_text)

    if not DEBUG_CLASSIFIER:
        return intent, mood

    # Heuristic: call LLM only when rules look unsure
    text = user_text.lower()
    looks_emotional = any(
        w in text
        for w in ["feel", "feeling", "cry", "sad", "depressed", "anxious", "hopeless", "worthless"]
    )

    if intent == "general" or (mood == "neutral" and looks_emotional):
        try:
            llm_intent, llm_mood = llm_classify_intent_and_mood(user_text)
            if llm_intent in INTENT_LABELS and llm_intent != "general":
                intent = llm_intent
            if llm_mood in MOOD_LABELS and llm_mood != "neutral":
                mood = llm_mood
        except Exception:
            logger.exception("Error in LLM hybrid classifier")

    return intent, mood


def build_context_prompt(history: List[Dict[str, str]], language: str) -> str:
    """
    Turn recent conversation into a short context block
    and add language instructions.
    history: list of {'role': 'user'|'bot', 'text': str}
    """
    history = history or []

    # Language instruction
    lang_instruction = ""
    if language and language != "auto":
        if language.startswith("hi"):
            lang_instruction = (
                "Respond primarily in Hindi (simple and friendly), but you may mix English "
                "for technical or academic terms.\n"
            )
        elif language.startswith("en"):
            lang_instruction = "Respond in clear, simple English.\n"

    if not history:
        return lang_instruction

    lines = []
    # Take last 6 turns to keep prompt short
    for turn in history[-4:]:
        role = "Student" if turn.get("role") == "user" else "MindMate"
        text = turn.get("text", "")
        lines.append(f"{role}: {text}")

    history_text = "\n".join(lines)

    return (
        lang_instruction
        + "Here is the recent conversation between the student and MindMate:\n"
        + history_text
        + "\n\nContinue the conversation in a supportive, kind tone.\n"
    )

def llm_classify_intent_and_mood(user_text: str) -> Tuple[str, str]:
    """
    Use the LLM as a classifier to refine intent/mood.
    Returns (intent, mood).
    """
    system_msg = (
        "You are a classifier for a mental health + academic assistant called MindMate. "
        "You ONLY output JSON. "
        "Given a student's message, label:\n"
        f"- intent: one of {INTENT_LABELS}\n"
        f"- mood: one of {MOOD_LABELS}\n"
        "Explain nothing. Do not add extra keys."
    )

    user_msg = (
        "Message: " + user_text + "\n\n"
        "Return JSON like: {\"intent\": \"exam_stress\", \"mood\": \"negative\"}"
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    try:
        raw = chat_with_ollama(messages).strip()
    except Exception:
        logger.exception("LLM intent classifier error:")
        return "general", "neutral"

    import json

    intent = "general"
    mood = "neutral"
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            if data.get("intent") in INTENT_LABELS:
                intent = data["intent"]
            if data.get("mood") in MOOD_LABELS:
                mood = data["mood"]
    except Exception:
        logger.warning("Could not parse classifier JSON: %r", raw)

    return intent, mood

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
            reply_lines.append(f"- {r['name']} ({r['available_hours']}): {r['phone']}")
        reply_lines.append(
            "If you feel in serious danger, please contact emergency services or a trusted person immediately."
        )
        return "\n".join(reply_lines), "helplines"

    return None, None

def get_llm_response(
    user_text: str,
    mode: str = "auto",
    language: str = "auto",
    history: Optional[List[Dict[str, str]]] = None,
) -> tuple[str, str, str]:
    """
    Main entry for the backend.
    Returns (reply_text, intent, mood_tag).

    mode: "auto", "wellbeing", "academics"
    language: "auto", "en", "hi", etc. (from user settings)
    history: recent conversation [{'role': 'user'|'bot', 'text': str}, ...]
    """
    if not user_text.strip():
        return "Please type something so I can help.", "general", "neutral"

    # Normalize mode
    mode = (mode or "auto").lower()
    if mode not in ("auto", "wellbeing", "academics"):
        mode = "auto"

    history = history or []

    # 1) Detect intent + mood via classifier wrapper
    intent, mood = classify_intent_and_mood(user_text)

    # Adjust intent priority based on mode (simple biasing)
    if mode == "wellbeing" and intent in ("pyqs", "projects", "syllabus", "notices", "deadlines", "academics"):
        intent = "wellbeing"
    elif mode == "academics" and intent not in ("pyqs", "projects", "syllabus", "notices", "deadlines"):
        intent = "academics"

    # 2) Rule-based academic / utility reply first
    rb_reply, rb_intent = rule_based_academics_reply(user_text)
    if rb_reply:
        final_intent = rb_intent or intent
        return rb_reply, final_intent, mood

    # 3) Build system prompt based on mode and mood
    system_prompt = SYSTEM_PROMPT

    if mode == "wellbeing":
        system_prompt += (
            "\nYou are currently in WELLBEING mode: "
            "prioritize emotional support, grounding exercises, and coping strategies. "
            "Keep answers short, empathetic, and student-friendly."
        )
    elif mode == "academics":
        system_prompt += (
            "\nYou are currently in ACADEMICS mode: "
            "prioritize syllabus help, PYQs, deadlines, and project guidance. "
            "Still be kind and supportive, but focus mainly on academic clarity."
        )

    if mood == "crisis_risk":
        system_prompt += (
            "\nThe student may be at some risk or talking about self-harm. "
            "Stay very gentle, encourage them to reach out to a trusted person or professional, "
            "and do not provide instructions for self-harm."
        )
    elif mood == "negative":
        system_prompt += (
            "\nThe student seems low, anxious, or stressed. "
            "Validate their feelings and offer simple, practical coping steps."
        )

    # 4) Add conversation context and language preference
    context_prompt = build_context_prompt(history, language)

    messages = [
        {"role": "system", "content": system_prompt},
    ]
    if context_prompt:
        messages.append({"role": "system", "content": context_prompt})
    messages.append({"role": "user", "content": user_text})

    # 5) Call LLM
    try:
        reply = chat_with_ollama(messages).strip()
    except Exception:
        logger.exception("LLM error:")
        reply = (
            "I'm having a bit of trouble thinking right now, but I'm here with you. "
            "Could you try rephrasing or asking in a slightly different way? "
            "Or please try again in a moment."
        )

    return reply, intent, mood

