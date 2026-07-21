"""
Orchestration layer: takes a user-supplied topic, builds the right prompt,
calls Gemini, and returns the parsed (but not yet validated) JSON.

form_generator.py is responsible for validating/normalizing that JSON into
a form that's safe to render.
"""
from config import Config
from utils.gemini_client import generate_json
from utils.prompt_builder import build_question_generation_prompt


def generate_questions_json(topic: str, num_questions: int = None) -> dict:
    """
    Ask Gemini to generate a feedback form for `topic`.
    Returns the raw parsed JSON dict (title/description/questions).
    Raises ValueError if Gemini's response can't be parsed as JSON.
    """
    num_questions = num_questions or Config.DEFAULT_NUM_QUESTIONS
    prompt = build_question_generation_prompt(topic, num_questions)
    return generate_json(prompt, temperature=0.7)
