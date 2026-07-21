"""
Turns one form's raw + sentiment/keyword-scored feedback DataFrame into
small JSON-safe dicts that the dashboard template hands straight to
Chart.js. No image rendering is done server-side -- charts render
client-side for interactivity.
"""
import json
from collections import Counter

import pandas as pd

from forms.form_generator import load_form


def sentiment_distribution(df: pd.DataFrame) -> dict:
    """{'labels': ['positive','neutral','negative'], 'counts': [..]}"""
    if df.empty or "sentiment" not in df.columns:
        return {"labels": [], "counts": []}
    counts = df["sentiment"].fillna("neutral").value_counts()
    order = ["positive", "neutral", "negative"]
    labels = [l for l in order if l in counts.index] + [
        l for l in counts.index if l not in order
    ]
    return {"labels": labels, "counts": [int(counts[l]) for l in labels]}


def average_sentiment_score(df: pd.DataFrame) -> float:
    if df.empty or "score" not in df.columns:
        return 0.0
    return round(float(pd.to_numeric(df["score"], errors="coerce").mean() or 0.0), 3)


def rating_question_averages(df: pd.DataFrame, form_id: str) -> dict:
    """{'labels': [question label, ...], 'averages': [3.8, 4.1, ...]}"""
    form = load_form(form_id)
    if not form or df.empty:
        return {"labels": [], "averages": []}

    rating_questions = [q for q in form["questions"] if q["type"] == "rating"]
    labels, averages = [], []
    for q in rating_questions:
        if q["id"] not in df.columns:
            continue
        values = pd.to_numeric(df[q["id"]], errors="coerce").dropna()
        if values.empty:
            continue
        labels.append(q["label"])
        averages.append(round(float(values.mean()), 2))
    return {"labels": labels, "averages": averages}


def responses_over_time(df: pd.DataFrame) -> dict:
    """{'labels': ['2026-07-14', ...], 'counts': [3, 5, ...]} grouped by day."""
    if df.empty or "submitted_at" not in df.columns:
        return {"labels": [], "counts": []}
    dates = pd.to_datetime(df["submitted_at"], errors="coerce", utc=True).dt.date
    counts = dates.value_counts().sort_index()
    return {
        "labels": [str(d) for d in counts.index],
        "counts": [int(c) for c in counts.values],
    }


def top_keywords(df: pd.DataFrame, limit: int = 15) -> dict:
    """
    {'labels': [keyword, ...], 'counts': [n, ...]} -- the most frequently
    mentioned AI-extracted keywords/themes across this form's responses,
    most common first.
    """
    if df.empty or "keywords" not in df.columns:
        return {"labels": [], "counts": []}

    counter = Counter()
    for raw in df["keywords"].dropna():
        try:
            words = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            continue
        for w in words or []:
            w = str(w).strip().lower()
            if w:
                counter[w] += 1

    top = counter.most_common(limit)
    return {"labels": [w for w, _ in top], "counts": [c for _, c in top]}


def dashboard_summary(df: pd.DataFrame, form_id: str) -> dict:
    """One dict with everything the dashboard template needs, for one form."""
    return {
        "total_responses": int(len(df)),
        "avg_sentiment_score": average_sentiment_score(df),
        "sentiment_distribution": sentiment_distribution(df),
        "rating_averages": rating_question_averages(df, form_id),
        "responses_over_time": responses_over_time(df),
        "top_keywords": top_keywords(df),
    }
