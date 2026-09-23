"""Same cases as the mobile app's vehicle_colour_test.dart."""

from plate_ocr.src.vehicle_colour import (
    body_region, classify, classify_pixel, colours_compatible,
)

PLATE = (160, 200, 240, 230)
VEHICLE = (60, 40, 340, 280)


def photo(body, background=None):
    background = background or body
    image = [[background for _ in range(400)] for _ in range(300)]
    for y in range(40, 281):
        for x in range(60, 341):
            image[y][x] = body
    for y in range(200, 231):
        for x in range(160, 241):
            image[y][x] = (245, 245, 245)
    return image


def test_names_clear_paint_colours():
    cases = {
        (245, 245, 245): "white", (175, 178, 182): "silver",
        (110, 112, 115): "grey", (20, 20, 22): "black",
        (200, 30, 30): "red", (100, 20, 30): "maroon",
        (240, 130, 20): "orange", (240, 200, 30): "yellow",
        (40, 140, 60): "green", (30, 80, 170): "blue",
        (110, 70, 40): "brown",
    }
    for rgb, name in cases.items():
        assert classify_pixel(*rgb) == name, rgb


def test_reads_body_paint_not_the_plate():
    reading = classify(photo((30, 80, 170)), plate=PLATE, vehicle=VEHICLE)
    assert reading.colour == "blue"
    assert reading.is_reliable


def test_white_car_and_daylight_red_car():
    assert classify(photo((240, 240, 238)), plate=PLATE).colour == "white"
    red = classify(photo((200, 30, 30)), plate=PLATE)
    assert red.colour == "red" and not red.colour_cast and red.is_reliable


def test_dark_photo_is_low_light():
    reading = classify(photo((25, 25, 30), (10, 10, 10)), plate=PLATE)
    assert reading.low_light and not reading.is_reliable


def test_sodium_light_is_a_colour_cast():
    reading = classify(photo((150, 95, 40), (90, 55, 20)), plate=PLATE)
    assert reading.colour_cast and not reading.is_reliable


def test_no_plate_no_vehicle_no_colour():
    assert classify(photo((30, 80, 170))).colour is None


def test_body_region_stays_inside_vehicle():
    region = body_region(400, 300, plate=(0, 280, 80, 300), vehicle=VEHICLE)
    assert region[0] >= 60 and region[3] <= 280


def test_look_alike_colours():
    assert colours_compatible("white", "silver")
    assert colours_compatible("grey", "black")
    assert not colours_compatible("white", "red")
