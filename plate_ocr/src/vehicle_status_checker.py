from .plate_text_cleaner import clean_plate_text


REPORTED_PLATES = {"WPCA9876", "TEST999"}
SAFE_PLATES = {"ABC1234", "SAFE001"}


def check_vehicle_status(plate_text: str) -> str:
    """Return a mock vehicle status for prototype flows."""
    cleaned_plate = clean_plate_text(plate_text)

    if not cleaned_plate:
        return "Unknown"
    if cleaned_plate in REPORTED_PLATES:
        return "Reported"
    if cleaned_plate in SAFE_PLATES or len(cleaned_plate) >= 5:
        return "Safe"
    return "Unknown"
