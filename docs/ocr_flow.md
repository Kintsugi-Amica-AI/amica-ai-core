# OCR Flow

The Scan before you ride flow. Every step runs on the phone, and photos are never uploaded.

> **Status:** the plate finder (step 3) and the vehicle check (steps 1, 7–10) are built but switched off with `FeatureFlags.plateFinder` and `FeatureFlags.vehicleCheck` in `amica-mobile-app/lib/core/constants/feature_flags.dart`. Their models aren't trained yet. Train and export them with `notebooks/train_plate_detector.ipynb`, copy them into `amica-mobile-app/assets/models/`, and then turn the flags on. While the flags are off, the app runs steps 2 and 4–6 only (scan-frame crop → ML Kit → plate format → lookup), as before.

1. **What was I told? (optional):** the rider picks the vehicle type and colour the ride app showed, for example "White Toyota Axio, CAB-1234".
2. **Capture:** the camera takes a photo every 2 seconds, or when the shutter is tapped. Gallery photos also work.
3. **Plate finder:** a YOLO detector (`plate_detector.tflite`, trained in `plate_ocr/training`) looks at the whole photo and crops the plate with a small margin. Small crops are enlarged for OCR. If the model isn't installed, or it finds no plate, the app falls back to the old scan-frame crop.
4. **OCR:** Google ML Kit reads the crop.
5. **Plate format:** `sri_lanka_plate.dart` checks the text against Sri Lankan formats (CAB-1234, KA-1234, WP CAB-1234, 65-1234). OCR look-alikes such as O/0, B/8 and I/1 are only ever suggested for the rider to confirm, never changed silently.
6. **Lookup:** the plate is checked against the `vehicles` collection to get its status, reports and ratings.
7. **Vehicle type:** the bundled COCO YOLOv8n (or `vehicle_detector_lk` with three-wheelers, when present) finds the vehicle that holds the plate. A COCO class maps to every type it could be; a COCO "car" can be a car, a van or a three-wheeler.
8. **Colour:** no AI is used. Pixels from the body panel around and above the plate are sorted into 11 colour names, and the largest group wins. The check isn't trusted in dark photos, under amber street lights, or when no colour gets at least 35% of the pixels.
9. **Compare:** `vehicle_match.dart` compares what the camera saw with what the rider was told and with the plate's community profile.
   * **Match:** everything that could be checked fits.
   * **Mismatch:** a confident reading disagrees. Look-alike colours (white/silver, grey/black, red/maroon) never count.
   * **Not sure:** nothing could be checked. The normal plate result still applies.

   The app only warns and never blocks the ride.
10. **Community:** type and colour words, never photos, are saved to `vehicle_observations/{plate}_{uid}`, one per user per plate. The `onVehicleObservationCreated` function keeps `vehicles/{plate}.observedProfile`. A usual type or colour needs at least 3 agreeing scans making up 60% or more of the scans.

`plate_ocr/src/vehicle_colour.py` mirrors the app's colour classifier, so `plate_ocr/training/evaluate.py` can measure it offline.
