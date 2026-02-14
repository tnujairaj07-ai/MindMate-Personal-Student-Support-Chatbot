# backend/llm_ollama.py
import os
import ollama
from backend.config import Config

# Option A: read directly from env with a default-
# llm_ollama.py talks to the environment itself.
# Slightly more “quick and dirty”, easy to understand.
# If many files start doing this, config becomes scattered (harder to see all settings in one place).

# MODEL_NAME = os.environ.get("OLLAMA_MODEL_NAME", "llama3.2")


# OPTION B (cleaner): use central config only
# All important settings live in backend/config.py (single source of truth).
# Any future change (e.g., renaming env vars, adding validation) is done only in Config.
# Code in other modules doesn’t care about env names; they just use attributes.

MODEL_NAME = Config.LLM_MODEL_NAME

def chat_with_ollama(messages):
    response = ollama.chat(
        model=MODEL_NAME,
        messages=messages,
    )
    return response["message"]["content"]
