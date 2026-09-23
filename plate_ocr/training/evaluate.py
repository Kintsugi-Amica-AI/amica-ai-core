"""Before/after evaluation for the report.

Run it on 50-100 of your own test photos of real Sri Lankan vehicles, taken
in the day, at night and at an angle. List them in a CSV:

    image,plate,vehicle_type,colour,condition
    IMG_0001.jpg,CAB1234,car,white,day
    IMG_0002.jpg,QL4567,three_wheeler,green,night

``plate`` is the canonical registration (no dash or province). ``vehicle_type``
and ``colour`` use the app's words (see vehicle_colour.COLOURS and
VEHICLE_KINDS below). ``condition`` is any tag you want results grouped by.
If a YOLO label file with the plate box exists (``--boxes``), the plate-found
numbers use IoU. Otherwise "found" means any plate was detected.

    python evaluate.py --images test_photos --csv test_photos/labels.csv \
        --plate-weights runs/plate_detector/weights/best.pt --ocr easyocr

Before is today's app: OCR on the fixed scan-frame crop. After is the plate
finder crop. OCR here is EasyOCR, standing in for ML Kit, which only runs on
the phone. Treat read accuracy as a comparison between before and after, not
as the phone's exact number. Type uses the same COCO YOLOv8n the app bundles;
colour uses the Python mirror of the app's classifier.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from plate_ocr.src.vehicle_colour import classify, colours_compatible  # noqa: E402

PROVINCES = "WP|CP|SP|NP|EP|NW|NC|SG|UP"
COCO_KINDS = {
    "car": {"car", "van", "three_wheeler"},
    "motorcycle": {"motorbike", "three_wheeler"},
    "bus": {"bus", "van"},
    "truck": {"lorry", "van"},
}
VEHICLE_KINDS = ("car", "van", "bus", "lorry", "motorbike", "three_wheeler")


def canonical_plate(text: str) -> str:
    """Same rules as the app's SriLankaPlate.parse, simplified."""
    t = re.sub(r"[^A-Z0-9\-]", " ", text.upper())
    m = re.search(rf"(?:\b(?:{PROVINCES})\s*)?\b([A-Z]{{2,3}})\s*-?\s*([0-9]{{4}})\b", t)
    if m:
        return m.group(1) + m.group(2)
    m = re.search(r"\b([0-9]{1,3})\s*-\s*([0-9]{4})\b", t)
    return m.group(1) + m.group(2) if m else ""


def iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def coverage(inner, outer) -> float:
    ix = max(0.0, min(inner[2], outer[2]) - max(inner[0], outer[0]))
    iy = max(0.0, min(inner[3], outer[3]) - max(inner[1], outer[1]))
    area = (inner[2] - inner[0]) * (inner[3] - inner[1])
    return ix * iy / area if area > 0 else 0.0


def read_box(label: Path, w: int, h: int):
    if not label.exists():
        return None
    for line in label.read_text().splitlines():
        f = line.split()
        if len(f) >= 5:
            cx, cy, bw, bh = (float(v) for v in f[1:5])
            return ((cx - bw / 2) * w, (cy - bh / 2) * h,
                    (cx + bw / 2) * w, (cy + bh / 2) * h)
    return None


def inflate(box, fraction, w, h):
    bw, bh = box[2] - box[0], box[3] - box[1]
    return (max(0, box[0] - bw * fraction), max(0, box[1] - bh * fraction),
            min(w, box[2] + bw * fraction), min(h, box[3] + bh * fraction))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images", type=Path, required=True)
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--boxes", type=Path, default=None,
                    help="YOLO plate labels (default: <images>/../labels)")
    ap.add_argument("--plate-weights", type=Path, required=True)
    ap.add_argument("--vehicle-weights", default="yolov8n.pt")
    ap.add_argument("--frame", default="0.12,0.30,0.76,0.40",
                    help="scan frame as left,top,width,height fractions")
    ap.add_argument("--ocr", choices=["none", "easyocr"], default="none")
    ap.add_argument("--out", type=Path, default=Path("evaluation.csv"))
    args = ap.parse_args()

    from ultralytics import YOLO

    plate_model = YOLO(args.plate_weights)
    vehicle_model = YOLO(args.vehicle_weights)
    reader = None
    if args.ocr == "easyocr":
        import easyocr
        reader = easyocr.Reader(["en"], gpu=False)
    frame = [float(v) for v in args.frame.split(",")]
    boxes_dir = args.boxes or args.images.parent / "labels"

    def ocr(img: Image.Image) -> str:
        if reader is None:
            return ""
        return canonical_plate(" ".join(reader.readtext(np.asarray(img), detail=0)))

    rows = []
    for row in csv.DictReader(args.csv.open()):
        path = args.images / row["image"]
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        w, h = img.size
        pixels = np.asarray(img)
        truth = read_box(boxes_dir / f"{path.stem}.txt", w, h)
        frame_box = (frame[0] * w, frame[1] * h,
                     (frame[0] + frame[2]) * w, (frame[1] + frame[3]) * h)

        plates = plate_model(img, verbose=False)[0].boxes
        found = None
        if len(plates):
            found = tuple(plates.xyxy[int(plates.conf.argmax())].tolist())

        vehicles = vehicle_model(img, imgsz=320, verbose=False)[0]
        vehicle, vehicle_label, vehicle_conf = None, None, 0.0
        for box, cls, conf in zip(vehicles.boxes.xyxy.tolist(),
                                  vehicles.boxes.cls.tolist(),
                                  vehicles.boxes.conf.tolist()):
            label = vehicles.names[int(cls)]
            if label not in COCO_KINDS or conf < 0.30:
                continue
            holds = found and box[0] <= (found[0] + found[2]) / 2 <= box[2] \
                and box[1] <= (found[1] + found[3]) / 2 <= box[3]
            if vehicle is None or holds or (conf * (box[2] - box[0]) >
                                            vehicle_conf * (vehicle[2] - vehicle[0])):
                vehicle, vehicle_label, vehicle_conf = box, label, conf
                if holds:
                    break

        colour = classify(pixels, plate=found, vehicle=vehicle)
        result = {
            "image": row["image"],
            "condition": row.get("condition", ""),
            "found_before": (coverage(truth, frame_box) >= 0.9) if truth else "",
            "found_after": (iou(found, truth) >= 0.5 if truth else True)
            if found else False,
            "read_before": "", "read_after": "",
            "type_seen": vehicle_label or "",
            "type_ok": (row["vehicle_type"] in COCO_KINDS[vehicle_label]
                        if vehicle_label and vehicle_conf >= 0.5 else False),
            "colour_seen": colour.colour or "",
            "colour_unsure": not colour.is_reliable,
            "colour_ok": colour.is_reliable
            and colours_compatible(row["colour"], colour.colour),
        }
        if reader is not None:
            before = ocr(img.crop(frame_box))
            after = ocr(img.crop(inflate(found, 0.12, w, h))) if found else ""
            if not after:
                after = before  # the app falls back to the frame crop
            result["read_before"] = before == row["plate"]
            result["read_after"] = after == row["plate"]
        rows.append(result)

    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    groups = defaultdict(list)
    for r in rows:
        groups["all"].append(r)
        if r["condition"]:
            groups[r["condition"]].append(r)

    def rate(items, key):
        values = [r[key] for r in items if r[key] != ""]
        return f"{100 * sum(values) / len(values):.0f}% ({sum(values)}/{len(values)})" \
            if values else "-"

    print("\n| Group | n | Plate found before | Plate found after | Read before "
          "| Read after | Type right | Colour right | Colour not sure |")
    print("|---|---|---|---|---|---|---|---|---|")
    for name, items in groups.items():
        print(f"| {name} | {len(items)} | {rate(items, 'found_before')} | "
              f"{rate(items, 'found_after')} | {rate(items, 'read_before')} | "
              f"{rate(items, 'read_after')} | {rate(items, 'type_ok')} | "
              f"{rate(items, 'colour_ok')} | {rate(items, 'colour_unsure')} |")
    print(f"\nPer-image results: {args.out}")


if __name__ == "__main__":
    main()
