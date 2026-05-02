"""Acme Corp Policy RAG — Input/output guardrails.

Validates user input and ensures output quality.
"""

import re

# Maximum question length (characters)
MAX_QUESTION_LENGTH = 500

# Minimum question length
MIN_QUESTION_LENGTH = 3

# Keywords that suggest off-topic questions
OFF_TOPIC_PATTERNS = [
    r"\b(write|generate|create)\s+(code|program|script|function)\b",
    r"\b(python|javascript|java|html|css|sql)\s+(code|script|program)\b",
    r"\brecipe\b",
    r"\bweather\b",
    r"\bstock\s*(price|market)\b",
    r"\bsports?\s*(score|result)\b",
    r"\b(tell|write)\s+(me\s+)?(a\s+)?(joke|story|poem)\b",
    r"\bwho\s+(is|was)\s+the\s+president\b",
    r"\bcapital\s+of\b",
    r"\btranslate\b",
    r"\bsolve\b.*\b(equation|math)\b",
]

# Compiled patterns for efficiency
_OFF_TOPIC_RE = [re.compile(p, re.IGNORECASE) for p in OFF_TOPIC_PATTERNS]


def validate_input(question: str) -> dict:
    """Validate user input.

    Returns:
        dict with 'valid' (bool) and 'error' (str or None).
    """
    if not question or not question.strip():
        return {"valid": False, "error": "Please enter a question."}

    question = question.strip()

    if len(question) < MIN_QUESTION_LENGTH:
        return {"valid": False, "error": "Your question is too short. Please provide more detail."}

    if len(question) > MAX_QUESTION_LENGTH:
        return {
            "valid": False,
            "error": f"Your question is too long ({len(question)} characters). "
            f"Please keep it under {MAX_QUESTION_LENGTH} characters.",
        }

    # Check for off-topic patterns
    for pattern in _OFF_TOPIC_RE:
        if pattern.search(question):
            return {
                "valid": False,
                "error": (
                    "I can only answer questions about Acme Corp company "
                    "policies and procedures. Please rephrase your question "
                    "or contact HR for other inquiries."
                ),
            }

    return {"valid": True, "error": None}


def validate_output(answer: str) -> str:
    """Post-process and validate the LLM output.

    Ensures the answer doesn't exceed length limits and
    contains citation markers.
    """
    if not answer:
        return (
            "I wasn't able to generate a response. Please try rephrasing "
            "your question or contact HR at hr@acmecorp.com."
        )

    # Truncate if extremely long (shouldn't happen with max_tokens, but safety net)
    max_chars = 4000
    if len(answer) > max_chars:
        answer = answer[:max_chars].rsplit(" ", 1)[0] + "..."

    # Check if answer contains at least one citation
    has_citation = bool(re.search(r"\[[\w\-]+\]", answer))
    if not has_citation:
        # The LLM might not have cited — check if it's an out-of-scope response
        out_of_scope_indicators = [
            "I don't have enough information",
            "I can only answer questions about",
            "not covered in our policy documents",
            "contact HR",
        ]
        is_out_of_scope = any(ind.lower() in answer.lower() for ind in out_of_scope_indicators)
        if not is_out_of_scope:
            answer += (
                "\n\n*Note: Please verify this information with the "
                "relevant policy document or contact HR at hr@acmecorp.com.*"
            )

    return answer
