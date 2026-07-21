"""
Thin wrapper around google-generativeai so the rest of the app never talks
to the SDK directly. Centralizes API-key setup, JSON-cleanup, and error
handling.
"""
import json
import re

from config import Config

_configured = False
genai = None  # imported lazily so the rest of the app works without the SDK installed


def _ensure_configured():
    global _configured, genai
    if not _configured:
        if genai is None:
            import google.generativeai as _genai
            genai = _genai
        if not Config.GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file."
            )
        genai.configure(api_key=Config.GEMINI_API_KEY)
        _configured = True


def _strip_code_fences(text: str) -> str:
    """Gemini sometimes wraps JSON in ```json ... ``` fences. Strip them."""
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text.strip(), flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text.strip()).strip()
    return text


def generate_text(prompt: str, temperature: float = 0.7) -> str:
    """Call Gemini and return the raw text response."""
    _ensure_configured()
    model = genai.GenerativeModel(Config.GEMINI_MODEL)
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(temperature=temperature),
    )
    return response.text


def generate_json(prompt: str, temperature: float = 0.4):
    """Call Gemini and parse the response as JSON, raising on failure."""
    raw = generate_text(prompt, temperature=temperature)
    cleaned = _strip_code_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Gemini did not return valid JSON.\nRaw response:\n{raw}"
        ) from exc
