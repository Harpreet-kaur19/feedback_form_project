"""
CSV persistence for submitted feedback.

Storage shape: one CSV per form (feedback/<form_id>.csv). Each file has
one row per submission, one column per question id, plus metadata
columns (response_id, submitted_at, form_id, topic). Because every form
gets its own file, there's no need to reconcile different forms'
question ids into a shared header anymore.
"""
import csv
import os
import uuid
from datetime import datetime, timezone

import pandas as pd

from config import Config

META_COLUMNS = ["response_id", "submitted_at", "form_id", "topic"]


def _feedback_path(form_id: str) -> str:
    return os.path.join(Config.FEEDBACK_DIR, f"{form_id}.csv")


def _read_existing_rows(form_id: str) -> list[dict]:
    path = _feedback_path(form_id)
    if not os.path.exists(path):
        return []
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_response(form: dict, answers: dict) -> str:
    """
    Append one submission to this form's own CSV.
    `answers` maps question_id -> submitted value (string).
    Returns the generated response_id.
    """
    Config.ensure_dirs()
    form_id = form.get("form_id", "")

    response_id = str(uuid.uuid4())
    row = {
        "response_id": response_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "form_id": form_id,
        "topic": form.get("topic", ""),
    }
    for q in form["questions"]:
        row[q["id"]] = answers.get(q["id"], "")

    existing_rows = _read_existing_rows(form_id)
    all_columns = list(META_COLUMNS)
    for q in form["questions"]:
        if q["id"] not in all_columns:
            all_columns.append(q["id"])
    for r in existing_rows:
        for key in r:
            if key not in all_columns:
                all_columns.append(key)

    existing_rows.append(row)

    with open(_feedback_path(form_id), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_columns)
        writer.writeheader()
        for r in existing_rows:
            writer.writerow({col: r.get(col, "") for col in all_columns})

    return response_id


def load_responses(form_id: str) -> pd.DataFrame:
    """Return one form's stored feedback as a DataFrame (empty if none)."""
    path = _feedback_path(form_id)
    if not os.path.exists(path):
        return pd.DataFrame(columns=META_COLUMNS)
    return pd.read_csv(path)


def load_all_responses() -> pd.DataFrame:
    """
    Return every form's feedback concatenated together. Only used where a
    deliberate cross-form view is wanted -- the normal dashboard/analysis
    flow uses load_responses(form_id) for a single form.
    """
    Config.ensure_dirs()
    frames = []
    for name in os.listdir(Config.FEEDBACK_DIR):
        if name.endswith(".csv"):
            frames.append(pd.read_csv(os.path.join(Config.FEEDBACK_DIR, name)))
    if not frames:
        return pd.DataFrame(columns=META_COLUMNS)
    return pd.concat(frames, ignore_index=True, sort=False)


def question_columns(df: pd.DataFrame) -> list[str]:
    """All non-metadata columns, i.e. actual question ids."""
    return [c for c in df.columns if c not in META_COLUMNS]
