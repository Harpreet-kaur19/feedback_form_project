import json

from flask import Flask, redirect, render_template, request, url_for, flash

from config import Config
from forms.form_generator import FormValidationError, generate_form, list_forms, load_form
from feedback.save_response import save_response
from sentiment.sentiment import analyze_form_feedback
from charts.charts import dashboard_summary

app = Flask(__name__)
app.config.from_object(Config)
Config.ensure_dirs()


@app.route("/", methods=["GET"])
def index():
    """User enters a topic/prompt to generate a feedback form."""
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    """Call Gemini to turn the user's prompt into a form definition."""
    topic = request.form.get("topic", "").strip()
    num_questions = request.form.get("num_questions", type=int)

    if not topic:
        flash("Please describe what you'd like feedback on.", "error")
        return redirect(url_for("index"))

    try:
        form = generate_form(topic, num_questions)
    except FormValidationError as exc:
        flash(f"Couldn't build a valid form: {exc}", "error")
        return redirect(url_for("index"))
    except Exception as exc:  # Gemini/network errors
        flash(f"Form generation failed: {exc}", "error")
        return redirect(url_for("index"))

    share_link = url_for("fill_form", form_id=form["form_id"], _external=True)
    return render_template("generated_form.html", form=form, share_link=share_link)


@app.route("/forms", methods=["GET"])
def forms_list():
    """Every form ever generated, with links to open/share/review each one."""
    return render_template("forms_list.html", forms=list_forms())


@app.route("/form/<form_id>", methods=["GET"])
def fill_form(form_id):
    """Render one specific generated form for users to fill out."""
    form = load_form(form_id)
    if not form:
        flash("That form doesn't exist or was never generated.", "error")
        return redirect(url_for("index"))
    return render_template("fill_form.html", form=form)


@app.route("/submit/<form_id>", methods=["POST"])
def submit(form_id):
    """Save a user's submitted answers to that form's own CSV."""
    form = load_form(form_id)
    if not form:
        flash("That form doesn't exist or was never generated.", "error")
        return redirect(url_for("index"))

    answers = {}
    for q in form["questions"]:
        answers[q["id"]] = request.form.get(q["id"], "").strip()
        if q["required"] and not answers[q["id"]]:
            flash(f"Please answer: {q['label']}", "error")
            return render_template("fill_form.html", form=form, answers=answers)

    save_response(form, answers)
    flash("Thanks! Your feedback was submitted.", "success")
    return redirect(url_for("fill_form", form_id=form_id))


@app.route("/dashboard/<form_id>", methods=["GET"])
def dashboard(form_id):
    """Run sentiment + keyword analysis on one form's responses and show charts."""
    form = load_form(form_id)
    if not form:
        flash("That form doesn't exist or was never generated.", "error")
        return redirect(url_for("forms_list"))
    df = analyze_form_feedback(form_id)
    summary = dashboard_summary(df, form_id)
    return render_template("dashboard.html", summary=summary, form=form)


@app.route("/analysis/<form_id>", methods=["GET"])
def analysis(form_id):
    """Detailed, per-response table with sentiment + keyword labels."""
    form = load_form(form_id)
    if not form:
        flash("That form doesn't exist or was never generated.", "error")
        return redirect(url_for("forms_list"))

    df = analyze_form_feedback(form_id)
    records = []
    if not df.empty:
        for r in df.to_dict(orient="records"):
            kw = r.get("keywords")
            if isinstance(kw, str):
                try:
                    r["keywords"] = json.loads(kw)
                except (json.JSONDecodeError, TypeError):
                    r["keywords"] = []
            records.append(r)

    return render_template("analysis.html", records=records, form=form)


@app.route("/api/refresh-sentiment/<form_id>", methods=["POST"])
def refresh_sentiment(form_id):
    """Force re-scoring of one form's feedback (bypasses the sentiment cache)."""
    analyze_form_feedback(form_id, force_refresh=True)
    return redirect(url_for("dashboard", form_id=form_id))


if __name__ == "__main__":
    app.run(debug=True)
