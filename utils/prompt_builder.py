"""
Generic, reusable prompt-string builders.

Kept separate from forms/prompt_generator.py so the *wording* of prompts
lives in one place, while forms/prompt_generator.py owns the *orchestration*
(calling Gemini, retrying, parsing).
"""


def build_question_generation_prompt(topic: str, num_questions: int = 5) -> str:
    """Prompt asking Gemini to produce a feedback form as strict JSON."""
    return f"""You are an expert survey designer. Create a feedback form about the
following topic:

TOPIC: "{topic}"

Generate exactly {num_questions} questions that would help collect useful,
actionable feedback about this topic. Mix question types so the form isn't
repetitive.

Return ONLY valid JSON (no markdown fences, no commentary) matching this
exact schema:

{{
  "title": "string - short form title",
  "description": "string - one sentence description of the form",
  "questions": [
    {{
      "id": "q1",
      "label": "string - the question text",
      "type": "text | textarea | rating | multiple_choice | yes_no",
      "options": ["only present when type is multiple_choice"],
      "required": true
    }}
  ]
}}

Rules:
- "type" must be one of: text, textarea, rating, multiple_choice, yes_no
- "rating" questions are on a 1-5 scale, do not include "options" for them
- Include at least one "rating" question and at least one open-ended
  "textarea" question so sentiment analysis has something to work with
- Keep labels concise and clear
- Output raw JSON only
"""


def build_sentiment_prompt(feedback_text: str) -> str:
    """Prompt asking Gemini to classify sentiment + extract keywords for one text."""
    return f"""Analyze the sentiment of the following user feedback and extract its
main themes as keywords.

FEEDBACK: "{feedback_text}"

Return ONLY valid JSON (no markdown fences, no commentary) matching this
exact schema:

{{
  "sentiment": "positive | neutral | negative",
  "score": 0.0,
  "summary": "one short sentence summarizing why",
  "keywords": ["short keyword or phrase", "..."]
}}

"score" must be a float between -1.0 (very negative) and 1.0 (very positive).
"keywords" should be 2-5 short, lowercase keywords or phrases capturing the
main topics/themes mentioned (e.g. "loading speed", "customer support").
If the feedback is empty or has no clear theme, return an empty list.
Output raw JSON only.
"""


def build_batch_sentiment_prompt(feedback_items: list[str]) -> str:
    """Prompt for classifying sentiment + extracting keywords for many texts at once."""
    numbered = "\n".join(f"{i+1}. {text}" for i, text in enumerate(feedback_items))
    return f"""Analyze the sentiment of each numbered feedback item below and extract
its main themes as keywords.

FEEDBACK ITEMS:
{numbered}

Return ONLY valid JSON (no markdown fences, no commentary): a JSON array
where each element matches this schema, in the same order as the input:

[
  {{
    "sentiment": "positive | neutral | negative",
    "score": 0.0,
    "summary": "one short sentence",
    "keywords": ["short keyword or phrase", "..."]
  }}
]

"keywords" should be 2-5 short, lowercase keywords or phrases capturing the
main topics/themes mentioned in that specific item. If an item is empty or
has no clear theme, use an empty list for it.
Output raw JSON only.
"""
