import re


def clean_plate_text(text: str) -> str:
    """Normalize OCR output to uppercase alphanumeric plate text."""
    if not text:
        return ""

    return re.sub(r"[^A-Za-z0-9]", "", text).upper()
