# Plate OCR

Prototype OCR helpers for Scan Before You Ride.

The current implementation contains deterministic placeholder functions for text cleaning and vehicle status mock checks. Real OCR models and image processing pipelines should be added after dataset and deployment decisions are complete.

## Vehicle check (plate finder, type and colour)

* `src/vehicle_colour.py`: a Python mirror of the app's body-colour classifier, with tests in `tests/test_vehicle_colour.py`.
* `training/`: scripts to prepare the dataset, train, export to TFLite and evaluate the plate finder and the optional Sri Lanka vehicle model. See `training/README.md`.
* The full on-phone flow is described in `../docs/ocr_flow.md`.
