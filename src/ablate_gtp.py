from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image


VARIANTS = {
    "baseline": {"mode": "fixed", "beta": 1.0, "description": "Official GTP trajectory channel weight used as the reporting baseline."},
    "zero": {"mode": "fixed", "beta": 0.0, "description": "Remove the trajectory channel."},
    "weak": {"mode": "fixed", "beta": 0.5, "description": "Suppress global trajectory memory."},
    "fixed1": {"mode": "fixed", "beta": 1.0, "description": "Explicit beta=1.0 ablation for comparison with the named baseline."},
    "strong": {"mode": "fixed", "beta": 1.5, "description": "Amplify global trajectory memory."},
    "adaptive": {"mode": "adaptive", "beta0": 1.0, "beta_min": 0.6, "beta_max": 1.4, "description": "ATR-GTP event-density adaptive trajectory reweighting."},
    "adaptive_smooth": {"mode": "adaptive_smooth", "beta0": 1.0, "beta_min": 0.6, "beta_max": 1.4, "ema": 0.65, "description": "ATR-GTP with temporal smoothing on beta to reduce frame-to-frame jitter."},
}


def read_image(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    return np.asarray(image, dtype=np.float32) / 255.0


def save_image(array: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(array * 255.0, 0, 255).astype(np.uint8)
    Image.fromarray(clipped, mode="RGB").save(path)


def event_density(image: np.ndarray) -> float:
    return float(np.mean(image[:, :, 0] + image[:, :, 1]))


def beta_for_image(variant: str, density: float, density_ref: float) -> float:
    cfg = VARIANTS[variant]
    if cfg["mode"] == "fixed":
        return float(cfg["beta"])
    beta = float(cfg["beta0"]) * density_ref / max(density, 1e-6)
    return float(np.clip(beta, cfg["beta_min"], cfg["beta_max"]))


def transform_directory(input_dir: Path, output_dir: Path, variant: str) -> list[dict[str, float | str]]:
    image_paths = sorted([p for p in input_dir.rglob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg"}])
    if not image_paths:
        raise FileNotFoundError(f"No image files found in {input_dir}")
    densities = [event_density(read_image(path)) for path in image_paths]
    density_ref = float(np.mean(densities[: min(30, len(densities))])) if densities else 1.0
    rows = []
    previous_beta_by_parent: dict[Path, float] = {}
    for path, density in zip(image_paths, densities):
        image = read_image(path)
        beta = beta_for_image(variant, density, density_ref)
        if VARIANTS[variant]["mode"] == "adaptive_smooth":
            parent = path.parent
            prev = previous_beta_by_parent.get(parent, beta)
            ema = float(VARIANTS[variant].get("ema", 0.65))
            beta = ema * prev + (1.0 - ema) * beta
            previous_beta_by_parent[parent] = beta
        image[:, :, 2] = np.clip(image[:, :, 2] * beta, 0, 1)
        rel = path.relative_to(input_dir)
        save_image(image, output_dir / variant / rel)
        rows.append({"variant": variant, "file": str(rel).replace("\\", "/"), "event_density": density, "density_ref": density_ref, "beta": beta})
    return rows


def write_protocol(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with (out / "atr_gtp_protocol.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=["variant", "mode", "beta", "beta0", "beta_min", "beta_max", "ema", "description"], extrasaction="ignore")
        writer.writeheader()
        for name, cfg in VARIANTS.items():
            row = {"variant": name, "mode": "", "beta": "", "beta0": "", "beta_min": "", "beta_max": "", "ema": "", "description": ""}
            row.update(cfg)
            writer.writerow(row)
    (out / "atr_gtp_protocol.json").write_text(json.dumps(VARIANTS, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply ATR-GTP trajectory-channel ablations to 3-channel GTP images.")
    parser.add_argument("--input-dir", help="Directory containing 3-channel GTP images.")
    parser.add_argument("--output-dir", default="outputs/gtp_ablation", help="Output directory.")
    parser.add_argument("--variant", choices=sorted(VARIANTS), default="adaptive")
    parser.add_argument("--all", action="store_true", help="Run all variants.")
    parser.add_argument("--protocol-only", action="store_true", help="Only write the ablation protocol manifest.")
    args = parser.parse_args()

    out = Path(args.output_dir)
    write_protocol(out)
    if args.protocol_only:
        print(f"Wrote ATR-GTP protocol to {out}")
        return 0
    if not args.input_dir:
        raise SystemExit("--input-dir is required unless --protocol-only is used.")
    variants = sorted(VARIANTS) if args.all else [args.variant]
    all_rows = []
    for variant in variants:
        all_rows.extend(transform_directory(Path(args.input_dir), out, variant))
    with (out / "atr_gtp_transform_log.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=["variant", "file", "event_density", "density_ref", "beta"])
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Wrote {len(all_rows)} transformed image records to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
