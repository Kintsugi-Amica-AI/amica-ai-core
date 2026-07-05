import re


def normalize_phrase(text: str) -> str:
    """Normalize spoken text for phrase matching."""
    compact = re.sub(r"[^a-zA-Z0-9 ]", " ", text).lower()
    return " ".join(compact.split())


def matches_secret_phrase(transcript: str, secret_phrase: str) -> bool:
    """Return True when the normalized secret phrase appears in the transcript."""
    normalized_transcript = normalize_phrase(transcript)
    normalized_secret = normalize_phrase(secret_phrase)

    if not normalized_secret:
        return False

    return normalized_secret in normalized_transcript
