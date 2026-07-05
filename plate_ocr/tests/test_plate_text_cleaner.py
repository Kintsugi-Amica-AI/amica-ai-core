from plate_ocr.src.plate_text_cleaner import clean_plate_text


def test_clean_plate_text_removes_symbols_and_uppercases() -> None:
    assert clean_plate_text(" wp-ca 9876 ") == "WPCA9876"


def test_clean_plate_text_handles_empty_input() -> None:
    assert clean_plate_text("") == ""
