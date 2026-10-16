"""A small, self-generated GTP example; no external tracker or dataset."""
from pathlib import Path
import tempfile
import numpy as np
from PIL import Image
from .ablate_gtp import transform_directory
from .metrics import iou_xywh


def main():
    with tempfile.TemporaryDirectory(prefix="atr_gtp_synthetic_") as tmp:
        root = Path(tmp)
        source = root / "input"
        source.mkdir()
        for i in range(4):
            frame = np.zeros((32, 32, 3), dtype=np.uint8)
            frame[8:16, 6+i:14+i, :2] = 100 + i*20
            frame[8:16, 4:14+i, 2] = 160
            Image.fromarray(frame).save(source / f"{i:04d}.png")
        rows = transform_directory(source, root / "output", "adaptive_smooth")
        assert len(rows) == 4
        assert all(0.6 <= float(row["beta"]) <= 1.4 for row in rows)
        boxes = np.array([[6., 8., 8., 8.], [7., 8., 8., 8.]])
        assert np.allclose(iou_xywh(boxes, boxes), 1.0)
        print("PASS: synthetic ATR-GTP transformation (4 frames) and identical-box IoU = 1")


if __name__ == "__main__":
    main()
