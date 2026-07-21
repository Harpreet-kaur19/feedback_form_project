"""
Runs Gemini sentiment + keyword analysis over the open-ended (text/textarea)
answers in a single form's feedback CSV. Results are cached per form in
sentiment_cache/<form_id>.csv, keyed by response_id, so reloading the
dashboard doesn't re-call the API for responses we've already scored.
"""
import json
import os

import pandas as pd

from config import Config
from utils.gemini_client import generate_json
from utils.prompt_builder import build_batch_sentiment_prompt, build_sentiment_prompt
from feedback.save_response import load_responses
from forms.form_generator import load_form

TEXT_QUESTION_TYPES = {"text", "textarea"}
CACHE_COLUMNS = ["response_id", "sentiment", "score", "summary", "keywords"]


def _cache_path(form_id: str) -> str:
    return os.path.join(Config.SENTIMENT_CACHE_DIR, f"{form_id}.csv")


def analyze_text(feedback_text: str) -> dict:
    """Analyze a single piece of text. Returns {sentiment, score, summary, keywords}."""
    if not feedback_text or not feedback_text.strip():
        return {"sentiment": "neutral", "score": 0.0, "summary": "No text provided.", "keywords": []}
    prompt = build_sentiment_prompt(feedback_text)
    return generate_json(prompt, temperature=0.2)


def _analyze_batch(texts: list[str]) -> list[dict]:
    """Analyze many texts (sentiment + keywords) in one Gemini call.
    Falls back to one-by-one analysis if the batch call fails or mismatches."""
    if not texts:
        return []
    prompt = build_batch_sentiment_prompt(texts)
    try:
        results = generate_json(prompt, temperature=0.2)
        if isinstance(results, list) and len(results) == len(texts):
            return results
    except ValueError:
        pass
    return [analyze_text(t) for t in texts]


def _load_cache(form_id: str) -> pd.DataFrame:
    path = _cache_path(form_id)
    if not os.path.exists(path):
        return pd.DataFrame(columns=CACHE_COLUMNS)
    return pd.read_csv(path)


def _save_cache(form_id: str, df: pd.DataFrame) -> None:
    Config.ensure_dirs()
    df.to_csv(_cache_path(form_id), index=False)


def _open_ended_column_ids(form: dict) -> list[str]:
    if not form:
        return []
    return [q["id"] for q in form["questions"] if q["type"] in TEXT_QUESTION_TYPES]


def analyze_form_feedback(form_id: str, force_refresh: bool = False) -> pd.DataFrame:
    """
    Returns one form's feedback DataFrame merged with sentiment + keyword
    columns (sentiment, score, summary, keywords) for each response.
    `keywords` is stored/returned as a JSON-encoded string per row; callers
    that need the list should json.loads() it (see charts.top_keywords
    and app.analysis for examples).
    """
    responses = load_responses(form_id)
    if responses.empty:
        return responses

    form = load_form(form_id)
    text_cols = _open_ended_column_ids(form)
    text_cols = [c for c in text_cols if c in responses.columns]

    cache = _load_cache(form_id) if not force_refresh else pd.DataFrame(columns=CACHE_COLUMNS)
    already_scored = set(cache["response_id"]) if not cache.empty else set()

    to_score = responses[~responses["response_id"].isin(already_scored)]

    if not to_score.empty and text_cols:
        new_rows = []
        for _, row in to_score.iterrows():
            combined_text = " ".join(
                str(row[c]) for c in text_cols if pd.notna(row.get(c)) and str(row[c]).strip()
            )
            new_rows.append({"response_id": row["response_id"], "text": combined_text})

        results = _analyze_batch([r["text"] for r in new_rows])
        new_cache_rows = []
        for meta, result in zip(new_rows, results):
            new_cache_rows.append(
                {
                    "response_id": meta["response_id"],
                    "sentiment": result.get("sentiment", "neutral"),
                    "score": result.get("score", 0.0),
                    "summary": result.get("summary", ""),
                    "keywords": json.dumps(result.get("keywords", [])),
                }
            )
        cache = pd.concat([cache, pd.DataFrame(new_cache_rows)], ignore_index=True)
        _save_cache(form_id, cache)

    return responses.merge(cache, on="response_id", how="left")
