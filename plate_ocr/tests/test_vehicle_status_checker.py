from plate_ocr.src.vehicle_status_checker import check_vehicle_status


def test_reported_vehicle_status() -> None:
    assert check_vehicle_status("wp ca 9876") == "Reported"


def test_unknown_vehicle_status_for_blank_plate() -> None:
    assert check_vehicle_status("") == "Unknown"
