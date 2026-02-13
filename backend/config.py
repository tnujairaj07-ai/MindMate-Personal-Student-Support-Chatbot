# backend/config.py
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, "..")

# Load .env from project root
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

    # Database
    DB_PATH = os.environ.get(
        "DB_PATH",
        os.path.join(PROJECT_ROOT, "chatbot.db")
    )

    # Demo / modes
    DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"
    LLM_MODE = os.environ.get("LLM_MODE", "local")  # or "online"

class DevConfig(Config):
    DEBUG = True
    SECRET_KEY = Config.SECRET_KEY or "dev-only-secret-key-change-this"

class ProdConfig(Config):
    DEBUG = False
    # In production, enforce presence of SECRET_KEY
    if not Config.SECRET_KEY:
        raise RuntimeError("SECRET_KEY must be set in environment for production")
    
def get_config():
    env = os.environ.get("FLASK_ENV", "development").lower()
    if env == "production":
        return ProdConfig()
    return DevConfig()
