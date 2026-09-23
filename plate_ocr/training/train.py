"""Train a small YOLO detector for the phone.

    python train.py --data datasets/plates/data.yaml --name plate_detector
    python train.py --data datasets/vehicles/data.yaml --name vehicle_detector_lk --imgsz 320

The plate finder defaults to 416 px input so plates seen from a few
metres away are still big enough to find. Vehicles are large, so 320 px
is enough and runs faster. Training starts from COCO-pretrained YOLOv8n
weights, which is what makes 241 images workable at all.

On a free Kaggle T4 GPU, 100 epochs on ~250 images take about 10 minutes.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--name", default="plate_detector")
    ap.add_argument("--model", default="yolov8n.pt",
                    help="starting weights (yolov8n.pt or yolo11n.pt)")
    ap.add_argument("--imgsz", type=int, default=416)
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default=None, help="0 for GPU, cpu for CPU")
    ap.add_argument("--fliplr", type=float, default=0.0,
                    help="horizontal flip chance: 0 for plates (text must not be "
                         "mirrored), 0.5 for vehicles")
    args = ap.parse_args()

    from ultralytics import YOLO

    model = YOLO(args.model)
    model.train(
        data=str(args.data),
        imgsz=args.imgsz,
        epochs=args.epochs,
        batch=args.batch,
        device=args.device,
        name=args.name,
        project=str(Path("runs").resolve()),
        exist_ok=True,
        patience=25,
        # Plates are read left-to-right, so no horizontal flips by default. Colour
        # jitter and small rotations/perspective mimic dusk, street
        # lights and angled shots.
        fliplr=args.fliplr,
        hsv_h=0.02, hsv_s=0.6, hsv_v=0.5,
        degrees=8.0, perspective=0.0008, scale=0.5,
    )
    # Newer Ultralytics nests `project` under runs/detect; ask the trainer.
    best = Path(model.trainer.save_dir) / "weights" / "best.pt"
    metrics = YOLO(best).val(data=str(args.data), imgsz=args.imgsz, split="test")
    print(f"\nBest weights: {best}")
    print(f"Test mAP50: {metrics.box.map50:.3f}  mAP50-95: {metrics.box.map:.3f}")
    print(f"Next: python export_tflite.py --weights {best} --name {args.name} "
          f"--imgsz {args.imgsz}")


if __name__ == "__main__":
    main()
