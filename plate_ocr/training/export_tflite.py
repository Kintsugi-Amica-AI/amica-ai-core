"""Export trained YOLO weights to the TFLite file the app loads.

    python export_tflite.py --weights runs/plate_detector/weights/best.pt \
        --name plate_detector --imgsz 416

Steps: YOLO -> ONNX (Ultralytics), ONNX -> TFLite (onnx2tf, float16
weights), then a check that the model runs and has the shape
amica-mobile-app's ``YoloDetector`` expects. ``<name>.tflite`` and
``<name>.txt`` (labels, one per line) are copied into
``amica-mobile-app/assets/models/``.

The ONNX route is used because the newer Ultralytics "litert" exporter
pins specific torch versions and often fails to install.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
DEFAULT_ASSETS = REPO / "amica-mobile-app" / "assets" / "models"
CALIBRATION = "calibration_image_sample_data_20x128x128x3_float32.npy"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", type=Path, required=True)
    ap.add_argument("--name", default="plate_detector",
                    help="plate_detector or vehicle_detector_lk")
    ap.add_argument("--imgsz", type=int, default=416)
    ap.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    ap.add_argument("--work", type=Path, default=Path("export"))
    args = ap.parse_args()

    from ultralytics import YOLO

    args.work.mkdir(parents=True, exist_ok=True)
    model = YOLO(args.weights)
    names = [model.names[i] for i in range(len(model.names))]
    onnx_path = Path(model.export(format="onnx", imgsz=args.imgsz,
                                  simplify=True, opset=17))

    # onnx2tf downloads random sample data for its own self-check; offline
    # or behind a proxy that download fails, so provide it locally.
    calibration = args.work / CALIBRATION
    if not calibration.exists():
        np.save(calibration,
                np.random.rand(20, 128, 128, 3).astype(np.float32))
    tf_dir = (args.work / f"{args.name}_tf").resolve()
    subprocess.run(
        # -nuo: skip onnx-simplifier. Ultralytics already simplified the
        # model with onnxslim, and onnxsim has no wheels for newer Pythons.
        [sys.executable, "-m", "onnx2tf", "-i", str(onnx_path.resolve()),
         "-o", str(tf_dir), "-nuo"],
        check=True, cwd=args.work,
    )
    tflite = tf_dir / f"{onnx_path.stem}_float16.tflite"

    check(tflite, args.imgsz, len(names))

    args.assets.mkdir(parents=True, exist_ok=True)
    shutil.copy(tflite, args.assets / f"{args.name}.tflite")
    (args.assets / f"{args.name}.txt").write_text("\n".join(names) + "\n")
    size_mb = tflite.stat().st_size / 1e6
    print(f"Copied {args.name}.tflite ({size_mb:.1f} MB) and {args.name}.txt "
          f"to {args.assets}")


def check(tflite: Path, imgsz: int, classes: int) -> None:
    """Fails loudly if the app would reject or misread the model."""
    try:
        from ai_edge_litert.interpreter import Interpreter
    except ImportError:
        from tensorflow.lite.python.interpreter import Interpreter

    interpreter = Interpreter(str(tflite))
    interpreter.allocate_tensors()
    inp = interpreter.get_input_details()[0]
    out = interpreter.get_output_details()[0]
    expected_in = [1, imgsz, imgsz, 3]
    if list(inp["shape"]) != expected_in or inp["dtype"] != np.float32:
        raise SystemExit(f"Input {inp['shape']} {inp['dtype']}, "
                         f"expected {expected_in} float32")
    if len(out["shape"]) != 3 or out["shape"][1] != classes + 4:
        raise SystemExit(f"Output {out['shape']}, expected [1, {classes + 4}, N]")
    interpreter.set_tensor(inp["index"],
                           np.full(expected_in, 114 / 255, np.float32))
    interpreter.invoke()
    print(f"TFLite check passed: {inp['shape']} -> {out['shape']}")


if __name__ == "__main__":
    main()
