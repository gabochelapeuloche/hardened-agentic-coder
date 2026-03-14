import re

# Patterns de secrets courants
SECRET_PATTERNS = [
    (r"(?i)(api[_-]?key|apikey)\s*[:=]\s*\S+", "[REDACTED_API_KEY]"),
    (r"(?i)(secret|password|passwd|pwd)\s*[:=]\s*\S+", "[REDACTED_SECRET]"),
    (r"ghp_[a-zA-Z0-9]{36}", "[REDACTED_GITHUB_TOKEN]"),
    (r"sk-[a-zA-Z0-9]{48}", "[REDACTED_OPENAI_KEY]"),
    (r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*\S+", "[REDACTED_AWS_SECRET]"),
    (r"[A-Za-z0-9+/]{40,}={0,2}", "[REDACTED_BASE64]"),  # base64 générique
]


def _redact(text: str) -> str:
    """Apply all redaction patterns to a text."""
    for pattern, replacement in SECRET_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text


def scrub_input(text: str) -> str:
    """Scrub secrets from a prompt before sending to the LLM.

    Args:
        text: The raw prompt text.

    Returns:
        The sanitized prompt with secrets redacted.
    """
    return _redact(text)


def scrub_output(text: str) -> str:
    """Scrub secrets from a diff before applying to the repo.

    Args:
        text: The raw diff text.

    Returns:
        The sanitized diff with secrets redacted.
    """
    return _redact(text)
