# backend/config.py
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, "..")

# Load .env once here
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

class Config:
    # Flask
    SECRET_KEY = os.environ["SECRET_KEY"]          # must exist
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

    # App modes
    DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"
    LLM_MODE = os.environ.get("LLM_MODE", "online")   # "online" / "local"
    LLM_MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "gpt-4o-mini")

    # Paths
    TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")
    STATIC_DIR = os.path.join(PROJECT_ROOT, "static")

class DevConfig(Config):
    DEBUG = True
    DEMO_MODE = True

class ProdConfig(Config):
    DEBUG = False
    # In prod, DEMO_MODE should be false in .env
