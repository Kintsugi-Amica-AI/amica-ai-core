"""Build a YOLO dataset for the plate finder (or the Sri Lanka vehicle model).

Sources, in YOLO format (one ``.txt`` label per image) or Pascal VOC
(one ``.xml`` per image, the usual format of Kaggle plate datasets):

* Roboflow "Srilankan Number Plates" (CC BY 4.0). Either download it
  here with your API key, or export it from Roboflow as "YOLOv8" and pass
  the unzipped folder with ``--source``.
* Your own photos (``--extra``), labelled in Roboflow, CVAT or Label Studio
  and exported as YOLO. This is how the group grows the 241 public images,
  and how three-wheelers are added for ``--task vehicles``.

For ``--task plates`` every class is merged into one class, ``plate``, so
it doesn't matter what a dataset called it ("number plate",
"License_Plate", ...). For ``--task vehicles`` class names are mapped
onto the app's six vehicle types with ``VEHICLE_ALIASES``, and anything
unknown is dropped.

Examples::

    python prepare_dataset.py --task plates \
        --roboflow-key $ROBOFLOW_API_KEY --workspace <ws> --project <proj> --version 1
    python prepare_dataset.py --task plates --source ~/Downloads/srilankan-plates \
        --extra ../samples/group_photos
    python prepare_dataset.py --task vehicles --source ~/tuktuk-labels --out datasets/vehicles_lk
"""

from __future__ import annotations

import argparse
import random
import re
import shutil
from pathlib import Path

import yaml

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

VEHICLE_CLASSES = ["car", "van", "bus", "lorry", "motorbike", "three_wheeler"]
VEHICLE_ALIASES = {
    "car": "car", "cars": "car", "sedan": "car", "hatchback": "car", "suv": "car",
    "jeep": "car",
    "van": "van", "vans": "van", "minivan": "van", "microbus": "van",
    "bus": "bus", "buses": "bus", "minibus": "bus",
    "lorry": "lorry", "truck": "lorry", "trucks": "lorry", "tipper": "lorry",
    "pickup": "lorry",
    "motorbike": "motorbike", "motorcycle": "motorbike", "motor_bike": "motorbike",
    "bike": "motorbike", "scooter": "motorbike",
    # Tuk-tuks go by many names across datasets ("Three-wheel" in the
    # Kaggle "Vehicle Dataset for YOLO", "autorickshaw" in IDD, "CNG" in
    # Bangladeshi datasets).
    "three_wheeler": "three_wheeler", "three_wheelers": "three_wheeler",
    "threewheeler": "three_wheeler", "three_wheel": "three_wheeler",
    "threewheel": "three_wheeler", "3_wheeler": "three_wheeler",
    "3wheeler": "three_wheeler", "tuk_tuk": "three_wheeler", "tuktuk": "three_wheeler",
    "tuk": "three_wheeler", "auto_rickshaw": "three_wheeler",
    "autorickshaw": "three_wheeler", "auto": "three_wheeler",
    "rickshaw": "three_wheeler", "cng": "three_wheeler",
}


def vehicle_type(name: str) -> str | None:
    """Maps a dataset's class name onto one of VEHICLE_CLASSES, or None.
    "Three-wheel", "three wheel" and "three_wheel" all become the same key."""
    key = re.sub(r"[\s\-]+", "_", name.strip().lower())
    return VEHICLE_ALIASES.get(key)


def download_roboflow(key: str, workspace: str, project: str, version: int,
                      dest: Path) -> Path:
    from roboflow import Roboflow  # imported here: optional dependency

    rf = Roboflow(api_key=key)
    dataset = rf.workspace(workspace).project(project).version(version) \
        .download("yolov8", location=str(dest))
    return Path(dataset.location)


def read_names(root: Path) -> list[str]:
    """Class names in index order: from data.yaml (or any YAML with
    ``names``), classes.txt or obj.names, searched two levels deep."""
    candidates = sorted(root.glob("*")) + sorted(root.glob("*/*"))
    for path in candidates:
        if path.suffix in (".yaml", ".yml") and path.is_file():
            try:
                names = (yaml.safe_load(path.read_text()) or {}).get("names")
            except (yaml.YAMLError, AttributeError):
                continue
            if isinstance(names, dict):
                return [str(names[k]) for k in sorted(names)]
            if isinstance(names, list) and names:
                return [str(n) for n in names]
    for path in candidates:
        if path.name in ("classes.txt", "obj.names", "classes.names"):
            names = [l.strip() for l in path.read_text().splitlines() if l.strip()]
            if names:
                return names
    return []

def _is_yolo_label(path: Path) -> bool:
    """A YOLO label has "class cx cy w h" lines, or is empty (no object).
    Some datasets ship .txt files with the plate text instead; those are
    not boxes."""
    try:
        lines = [l.split() for l in path.read_text(errors="ignore").splitlines()
                 if l.strip()]
    except OSError:
        return False
    return all(len(f) >= 5 and all(_is_number(v) for v in f) for f in lines)


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def find_pairs(root: Path) -> list[tuple[Path, Path, str]]:
    """(image, label, split) triples. The label is a YOLO .txt or a Pascal
    VOC .xml (the format of many Kaggle plate datasets), found next to the
    image, in a sibling ``labels`` folder, or anywhere under ``root`` in an
    ``annotations`` folder. Split is train/valid/test when the source
    already has one, else ''."""
    xml_by_stem: dict[str, Path] = {}
    for xml in root.rglob("*.xml"):
        xml_by_stem.setdefault(xml.stem, xml)

    pairs = []
    for image in sorted(root.rglob("*")):
        if image.suffix.lower() not in IMAGE_EXTS:
            continue
        parts = list(image.parts)
        candidates = []
        if "images" in parts:
            i = len(parts) - 1 - parts[::-1].index("images")
            candidates.append(
                Path(*parts[:i], "labels", *parts[i + 1:]).with_suffix(".txt"))
        candidates.append(image.with_suffix(".txt"))
        label = next((c for c in candidates
                      if c.exists() and _is_yolo_label(c)), None)
        if label is None:
            label = image.with_suffix(".xml")
            if not label.exists():
                label = xml_by_stem.get(image.stem)
        if label is None or not label.exists():
            continue
        split = next((s for s in ("train", "valid", "val", "test")
                      if s in [p.lower() for p in parts]), "")
        pairs.append((image, label, "valid" if split == "val" else split))
    return pairs


def _voc_boxes(label: Path) -> list[tuple[str, float, float, float, float]]:
    """Pascal VOC objects as (name, cx, cy, w, h), normalised to 0-1."""
    import xml.etree.ElementTree as ET

    root = ET.parse(label).getroot()
    size = root.find("size")
    width = float(size.findtext("width", "0")) if size is not None else 0.0
    height = float(size.findtext("height", "0")) if size is not None else 0.0
    if width <= 0 or height <= 0:
        from PIL import Image

        image = next((p for p in label.parent.parent.rglob(f"{label.stem}.*")
                      if p.suffix.lower() in IMAGE_EXTS), None)
        if image is None:
            return []
        width, height = Image.open(image).size
    boxes = []
    for obj in root.iter("object"):
        box = obj.find("bndbox")
        if box is None:
            continue
        x1, y1, x2, y2 = (float(box.findtext(k, "0"))
                          for k in ("xmin", "ymin", "xmax", "ymax"))
        if x2 <= x1 or y2 <= y1:
            continue
        boxes.append((obj.findtext("name", "plate"),
                      (x1 + x2) / 2 / width, (y1 + y2) / 2 / height,
                      (x2 - x1) / width, (y2 - y1) / height))
    return boxes


def remap(label: Path, names: list[str], task: str) -> list[str]:
    boxes: list[tuple[str, list[float]]] = []
    if label.suffix.lower() == ".xml":
        boxes = [(name, list(coords)) for name, *coords in _voc_boxes(label)]
    else:
        for raw in label.read_text().splitlines():
            fields = raw.split()
            if len(fields) < 5:
                continue
            cls = int(float(fields[0]))
            boxes.append((names[cls] if cls < len(names) else str(cls),
                          [float(v) for v in fields[1:]]))

    lines = []
    for name, coords in boxes:
        if task == "plates":
            new = 0
        else:
            mapped = vehicle_type(name)
            if mapped is None:
                continue
            new = VEHICLE_CLASSES.index(mapped)
        # Polygon labels (segmentation exports) become their bounding box.
        if len(coords) > 4:
            xs, ys = coords[0::2], coords[1::2]
            coords = [(min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2,
                      max(xs) - min(xs), max(ys) - min(ys)]
        coords = [min(max(v, 0.0), 1.0) for v in coords[:4]]
        lines.append(f"{new} " + " ".join(f"{v:.6f}" for v in coords))
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", choices=["plates", "vehicles"], default="plates")
    ap.add_argument("--source", type=Path, action="append", default=[],
                    help="YOLO-format folder (repeatable)")
    ap.add_argument("--extra", type=Path, action="append", default=[],
                    help="more YOLO-format folders, e.g. your own photos")
    ap.add_argument("--roboflow-key")
    ap.add_argument("--workspace")
    ap.add_argument("--project")
    ap.add_argument("--version", type=int, default=1)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--valid", type=float, default=0.15)
    ap.add_argument("--test", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--names", default="",
                    help="class names in index order, comma separated, when the "
                         "dataset has no data.yaml / classes.txt")
    args = ap.parse_args()

    out = args.out or Path("datasets") / args.task
    sources = list(args.source) + list(args.extra)
    if args.roboflow_key:
        if not (args.workspace and args.project):
            ap.error("--roboflow-key needs --workspace and --project")
        sources.insert(0, download_roboflow(args.roboflow_key, args.workspace,
                                            args.project, args.version,
                                            Path("downloads") / args.project))
    if not sources:
        ap.error("give --source, --extra or --roboflow-key")

    if out.exists():
        shutil.rmtree(out)
    rng = random.Random(args.seed)
    counts = {"train": 0, "valid": 0, "test": 0}
    with_boxes = 0
    for source in sources:
        names = args.names.split(",") if args.names else read_names(source)
        if args.task == "vehicles":
            print(f"{source.name}: classes {names or '(none found)'} -> "
                  f"{[vehicle_type(n) for n in names]}")
            if not names:
                raise SystemExit(f"No class names found in {source} (data.yaml, "
                                 "classes.txt). Pass them with --names car,van,...")
        for index, (image, label, split) in enumerate(sorted(find_pairs(source))):
            if not split:
                roll = rng.random()
                split = ("test" if roll < args.test else
                         "valid" if roll < args.test + args.valid else "train")
            lines = remap(label, names, args.task)
            if lines:
                with_boxes += 1
            stem = f"{source.name}_{index:05d}"
            (out / split / "images").mkdir(parents=True, exist_ok=True)
            (out / split / "labels").mkdir(parents=True, exist_ok=True)
            shutil.copy(image, out / split / "images" / f"{stem}{image.suffix.lower()}")
            (out / split / "labels" / f"{stem}.txt").write_text("\n".join(lines))
            counts[split] += 1

    # A source with only train/valid still needs a test split for evaluate.py.
    if counts["test"] == 0 and counts["valid"] > 1:
        # Shuffle first: datasets often name files by class, so taking the
        # first half in name order gives valid and test very different mixes.
        valid = sorted((out / "valid" / "images").iterdir())
        rng.shuffle(valid)
        (out / "test" / "images").mkdir(parents=True, exist_ok=True)
        (out / "test" / "labels").mkdir(parents=True, exist_ok=True)
        for image in valid[: len(valid) // 2]:
            label = out / "valid" / "labels" / f"{image.stem}.txt"
            shutil.move(image, out / "test" / "images" / image.name)
            shutil.move(label, out / "test" / "labels" / label.name)
            counts["valid"] -= 1
            counts["test"] += 1

    names = ["plate"] if args.task == "plates" else VEHICLE_CLASSES
    (out / "data.yaml").write_text(yaml.safe_dump({
        "path": str(out.resolve()),
        "train": "train/images", "val": "valid/images", "test": "test/images",
        "names": dict(enumerate(names)),
    }, sort_keys=False))
    total = sum(counts.values())
    print(f"{out}: {counts} images ({with_boxes} with boxes), classes {names}")
    if total == 0:
        raise SystemExit("No labelled images found. Expected YOLO .txt labels "
                         "or Pascal VOC .xml annotations next to the images.")
    if with_boxes < total / 2:
        print("WARNING: most images have no boxes - check the label format "
              "and class names.")


if __name__ == "__main__":
    main()
