import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """Central configuration for the app."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

    # Gemini API
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Storage paths
    DATA_DIR = os.path.join(BASE_DIR, "data")

    # One JSON file per generated form: forms/<form_id>.json
    # Archived permanently so shareable links never go stale, even after
    # newer forms are generated.
    FORMS_DIR = os.path.join(DATA_DIR, "forms")

    # One CSV per form: feedback/<form_id>.csv
    # Each form's responses live in their own file, so schemas never need
    # to be patched to accommodate another form's questions.
    FEEDBACK_DIR = os.path.join(DATA_DIR, "feedback")

    # One sentiment/keyword cache per form: sentiment_cache/<form_id>.csv
    SENTIMENT_CACHE_DIR = os.path.join(DATA_DIR, "sentiment_cache")

    # Points at the form_id of the most recently generated form. Purely a
    # convenience default -- every form remains reachable by its own id
    # regardless of what's "active".
    ACTIVE_FORM_POINTER = os.path.join(DATA_DIR, "active_form_id.txt")

    # Form generation defaults
    DEFAULT_NUM_QUESTIONS = 5

    @staticmethod
    def ensure_dirs():
        os.makedirs(Config.FORMS_DIR, exist_ok=True)
        os.makedirs(Config.FEEDBACK_DIR, exist_ok=True)
        os.makedirs(Config.SENTIMENT_CACHE_DIR, exist_ok=True)
