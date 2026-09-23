# Plate finder and vehicle model training

This folder trains the two optional detectors used by the app's Scan before you ride screen:

* `plate_detector`: finds the number plate anywhere in the photo, so the rider doesn't have to line it up inside the scan frame.
* `vehicle_detector`: the ready-made COCO YOLOv8n, exported for the phone. It knows car, motorcycle, bus and truck.
* `vehicle_detector_lk` (optional): a Sri Lanka fine-tune that adds `three_wheeler`, `van` and `lorry`. When present, the app uses it in place of `vehicle_detector`.

Everything runs on the phone as TFLite. No model ships with the app yet, and both features are off in `amica-mobile-app/lib/core/constants/feature_flags.dart` (`plateFinder` and `vehicleCheck`).

**The easiest route is the notebook** `../../notebooks/train_plate_detector.ipynb`. On Kaggle (GPU T4 x2, Internet on), it runs every step below, including exporting `vehicle_detector`, checks each model, and gives you a zip of the files for the app. The first cell explains how to attach this folder and a plate dataset as Kaggle inputs. The sections below show the same steps as plain commands.

After copying the models into `amica-mobile-app/assets/models/`, set the matching flag to `true`. If a model is still missing when its flag is on, the app falls back to the old behaviour, so a scan never gets worse.

## 1. Get the data

Download the [Srilankan Number Plates dataset on Roboflow Universe](https://universe.roboflow.com/). Search for "Srilankan Number Plates". It has about 241 images with a box around each plate, under the CC BY 4.0 licence, so credit it in the report and the app.

* **With an API key:** on the dataset page, go to *Download Dataset → YOLOv8 → Show download code*, and copy the workspace, project and version from the snippet.
* **Without a key:** download the zip in YOLOv8 format and unzip it.
* **From Kaggle:** a Sri Lankan plate dataset with Pascal VOC `.xml` annotations works too. `prepare_dataset.py` converts VOC to YOLO.

Add your group's own photos too. Label them in Roboflow, CVAT or Label Studio and export them as YOLO. More night, rain and angled shots help the most.

```bash
pip install -r requirements.txt
python prepare_dataset.py --task plates \
    --roboflow-key $ROBOFLOW_API_KEY --workspace <ws> --project <proj> --version 1 \
    --extra path/to/our_photos_yolo
# or: python prepare_dataset.py --task plates --source path/to/unzipped --extra ...
```

All classes are merged into one class called `plate`. If a split is missing, the script makes a 70/15/15 train/valid/test split.

## 2. Train

Training is quickest on a free Kaggle GPU. Open `../../notebooks/train_plate_detector.ipynb`, or run:

```bash
python train.py --data datasets/plates/data.yaml --name plate_detector --imgsz 416
```

Training starts from COCO-pretrained YOLOv8n weights. Augmentations stand in for dusk, street lights and angles. Horizontal flips are off because plate text shouldn't be mirrored. The script prints the test-set mAP at the end; put that number in the report.

## 3. Export to the app

```bash
python export_tflite.py --weights runs/plate_detector/weights/best.pt \
    --name plate_detector --imgsz 416
```

This writes `amica-mobile-app/assets/models/plate_detector.tflite` (about 6 MB) and `plate_detector.txt`, after checking that the shapes match what the app's `YoloDetector` expects. Rebuild the app and the plate finder is active.

## 4. Three-wheelers: `vehicle_detector_lk` (optional)

The COCO model has no three-wheeler class. It usually calls a tuk-tuk a "car" or a "motorcycle", so the app never flags a told three-wheeler as a mismatch in that case. To detect three-wheelers properly, train `vehicle_detector_lk`.

**Recommended dataset:** [Vehicle Dataset for YOLO](https://www.kaggle.com/datasets/nadinpethiyagoda/vehicle-dataset-for-yolo) on Kaggle, by Nadin Pethiyagoda, licence DbCL v1.0.

* It has 3,000 images, split into 2,100 train and 900 validation.
* It covers the app's six types: Car, Van, Bus, Truck, Motorbike and Three-wheel, with about 550–700 labelled vehicles per class.
* `prepare_dataset.py` maps its class names automatically: "Three-wheel" becomes `three_wheeler` and "Truck" becomes `lorry`.
* The images come from several sources, including web scraping and the Stanford Cars dataset. Most show one vehicle close up, which matches how the app scans. They aren't all Sri Lankan street scenes, so adding your own photos still helps.

**On Kaggle:** add the dataset with **+ Add Input**, set `TRAIN_THREE_WHEELER_MODEL = True` in section 1 of the notebook, and run it. Section 8b trains the model, prints per-class test scores (check `three_wheeler`), and exports `vehicle_detector_lk.tflite`.

**Locally:**

```bash
python prepare_dataset.py --task vehicles --source path/to/vehicle-dataset-for-yolo --out datasets/vehicles
python train.py --data datasets/vehicles/data.yaml --name vehicle_detector_lk --imgsz 320 --fliplr 0.5
python export_tflite.py --weights runs/vehicle_detector_lk/weights/best.pt \
    --name vehicle_detector_lk --imgsz 320
```

**Other sources, if you want more data:**

* IDD, the Indian Driving Dataset, has an `autorickshaw` class. Its roads and vehicles are close to Sri Lanka's. It needs registration and is for non-commercial research use only.
* Roboflow Universe has several auto-rickshaw datasets. Check each one's licence.
* Your own photos: label **every vehicle in every photo** with the six types. If you label only the tuk-tuks, the model forgets the other types.

Any class name in the recognised list maps automatically (for example `autorickshaw`, `tuk-tuk`, `CNG`, `Three-wheel`). Others are dropped, and the script prints the mapping so you can check it. If a dataset has no `data.yaml` or `classes.txt`, pass `--names` with the class names in order.

## 5. Measure before and after (for the report)

Take 50–100 test photos of real plates, spread across day, night and angled shots. They must not be in the training data. List them in a CSV (the format is in the docstring of `evaluate.py`), then run:

```bash
pip install easyocr   # stands in for ML Kit, which only runs on the phone
python evaluate.py --images test_photos --csv test_photos/labels.csv \
    --plate-weights runs/plate_detector/weights/best.pt --ocr easyocr
```

The script prints a table grouped by condition:

* how often the plate was found, before (scan frame) and after (plate finder)
* how often the plate was read correctly, before and after
* how often the type and colour were right
* how often the colour check said "not sure"

It also writes a per-image CSV.
