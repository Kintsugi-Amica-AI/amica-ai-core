from .image_preprocessing import prepare_image_for_ocr
from .plate_text_cleaner import clean_plate_text


def extract_plate_text(image_path: str) -> str:
    """Return cleaned OCR text for a plate image.

    TODO: Replace the placeholder with a real OCR model or provider call.
    """
    _prepared_image_path = prepare_image_for_ocr(image_path)
    raw_text = ""
    return clean_plate_text(raw_text)
