from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .ablate_gtp import VARIANTS, beta_for_image, event_density, read_image, save_image
from .metrics import compute_sequence_metrics, load_xywh


DEFAULT_SEQUENCES = ["star_motion", "bike_low", "dog_motion", "box_hdr", "star_mul222"]
DEFAULT_VARIANTS = ["baseline", "zero", "weak", "fixed1", "strong", "adaptive", "adaptive_smooth"]


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[1]


def copy_groundtruths(source_root: Path, target_root: Path) -> None:
    for seq_dir in sorted(source_root.iterdir()):
        gt = seq_dir / "groundtruth_rect.txt"
        if seq_dir.is_dir() and gt.exists():
            out_dir = target_root / seq_dir.name
            out_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(gt, out_dir / "groundtruth_rect.txt")


def transform_sequence_images(source_dir: Path, target_dir: Path, variant: str) -> list[dict[str, str | float]]:
    image_paths = sorted([p for p in source_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"}])
    if not image_paths:
        raise FileNotFoundError(f"No GTP images found in {source_dir}")
    densities = [event_density(read_image(path)) for path in image_paths]
    density_ref = float(np.mean(densities[: min(30, len(densities))]))
    previous_beta: float | None = None
    rows: list[dict[str, str | float]] = []
    target_dir.mkdir(parents=True, exist_ok=True)
    for path, density in zip(image_paths, densities):
        image = read_image(path)
        beta = beta_for_image(variant, density, density_ref)
        if VARIANTS[variant]["mode"] == "adaptive_smooth":
            prev = previous_beta if previous_beta is not None else beta
            ema = float(VARIANTS[variant].get("ema", 0.65))
            beta = ema * prev + (1.0 - ema) * beta
            previous_beta = beta
        image[:, :, 2] = np.clip(image[:, :, 2] * beta, 0, 1)
        save_image(image, target_dir / path.name)
        rows.append(
            {
                "variant": variant,
                "sequence": source_dir.parent.name,
                "frame": path.name,
                "event_density": density,
                "density_ref": density_ref,
                "beta": beta,
            }
        )
    return rows


def prepare_variant_dataset(source_root: Path, work_dir: Path, variant: str, sequences: list[str]) -> tuple[Path, list[dict[str, str | float]]]:
    if variant in {"baseline", "fixed1"}:
        return source_root, []
    dataset_root = work_dir / "datasets" / variant
    copy_groundtruths(source_root, dataset_root)
    rows: list[dict[str, str | float]] = []
    for sequence in sequences:
        src = source_root / sequence / "inter1_stack_3008"
        dst = dataset_root / sequence / "inter1_stack_3008"
        rows.extend(transform_sequence_images(src, dst, variant))
    return dataset_root, rows


def run_tracker(
    python: Path,
    official_root: Path,
    dataset_root: Path,
    results_root: Path,
    save_dir: Path,
    sequence: str,
    log_file: Path,
) -> None:
    env = os.environ.copy()
    env["SDTRACK_EOTB_PATH"] = str(dataset_root)
    env["SDTRACK_RESULTS_PATH"] = str(results_root)
    env["SDTRACK_SAVE_DIR"] = str(save_dir)
    env["SDTRACK_PRJ_DIR"] = str(official_root)
    cmd = [
        str(python),
        "tracking/test.py",
        "SDTrack",
        "SDTrack-tiny-fe108",
        "--dataset_name",
        "eotb",
        "--sequence",
        sequence,
        "--threads",
        "0",
        "--num_gpus",
        "1",
    ]
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as log:
        log.write("\n$ " + " ".join(cmd) + "\n")
        proc = subprocess.run(cmd, cwd=official_root, env=env, text=True, stdout=log, stderr=subprocess.STDOUT, check=False)
        log.write(f"\n[returncode] {proc.returncode}\n")
    if proc.returncode != 0:
        raise RuntimeError(f"Tracker failed for {sequence}; see {log_file}")


def evaluate_variant(pred_dir: Path, gt_dir: Path, out_dir: Path, variant: str) -> dict[str, float | int | str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "src.eval_sdtrack",
            "--pred",
            str(pred_dir),
            "--gt",
            str(gt_dir),
            "--out",
            str(out_dir),
            "--tracker-name",
            f"ATR-GTP-{variant}",
        ],
        check=True,
    )
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    summary["variant"] = variant
    return summary


def write_iou_curves(results_root: Path, gt_dir: Path, variants: list[str], sequence: str, out_file: Path) -> None:
    gt = load_xywh(gt_dir / f"{sequence}.txt")
    rows = []
    for variant in variants:
        pred_file = results_root / variant / "SDTrack" / "SDTrack-tiny-fe108" / f"{sequence}.txt"
        if not pred_file.exists():
            continue
        pred = load_xywh(pred_file)
        _, arrays = compute_sequence_metrics(sequence, pred, gt)
        for idx, iou in enumerate(arrays["iou"]):
            rows.append({"variant": variant, "sequence": sequence, "frame": idx, "iou": float(iou)})
    out_file.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_file, index=False, encoding="utf-8-sig")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run complete tracker inference for ATR-GTP variants on a fixed FE108 subset.")
    parser.add_argument("--repo-root", default=str(repo_root_from_here()))
    parser.add_argument("--source-root", default="data/FE108/test")
    parser.add_argument("--work-dir", default="outputs/atr_gtp_tracking")
    parser.add_argument("--sequences", nargs="*", default=DEFAULT_SEQUENCES)
    parser.add_argument("--variants", nargs="*", default=DEFAULT_VARIANTS)
    parser.add_argument("--skip-run", action="store_true", help="Only evaluate existing prediction files.")
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    source_root = (repo / args.source_root).resolve()
    work_dir = (repo / args.work_dir).resolve()
    official_root = repo / "external" / "SDTrack" / "SDTrack-Event"
    python = repo / ".venv" / "Scripts" / "python.exe"
    if not python.exists():
        python = Path(sys.executable)
    gt_dir = repo / "data" / "official_results_E" / "FE108_eval" / "FE108" / "annos" / "gt_rect"
    metrics_root = repo / "outputs" / "metrics" / "atr_gtp_tracker"
    results_root = work_dir / "results"
    log_file = repo / "outputs" / "logs" / "atr_gtp_tracker_eval.log"

    missing = [seq for seq in args.sequences if not (source_root / seq / "inter1_stack_3008").exists()]
    if missing:
        raise FileNotFoundError(f"Missing FE108 GTP sequence directories: {missing}")

    work_dir.mkdir(parents=True, exist_ok=True)
    transform_rows: list[dict[str, str | float]] = []
    summaries = []
    for variant in args.variants:
        dataset_root, rows = prepare_variant_dataset(source_root, work_dir, variant, args.sequences)
        transform_rows.extend(rows)
        variant_results = results_root / variant
        if not args.skip_run:
            for sequence in args.sequences:
                run_tracker(python, official_root, dataset_root, variant_results, repo / "outputs", sequence, log_file)
        pred_dir = variant_results / "SDTrack" / "SDTrack-tiny-fe108"
        summaries.append(evaluate_variant(pred_dir, gt_dir, metrics_root / variant, variant))

    if transform_rows:
        with (work_dir / "variant_transform_log.csv").open("w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=["variant", "sequence", "frame", "event_density", "density_ref", "beta"])
            writer.writeheader()
            writer.writerows(transform_rows)

    summary_df = pd.DataFrame(summaries)
    if "auc_micro" in summary_df:
        baseline_auc = float(summary_df.loc[summary_df["variant"] == "baseline", "auc_micro"].iloc[0])
        baseline_pr = float(summary_df.loc[summary_df["variant"] == "baseline", "pr20_micro"].iloc[0])
        summary_df["delta_auc"] = summary_df["auc_micro"] - baseline_auc
        summary_df["delta_pr20"] = summary_df["pr20_micro"] - baseline_pr
    metrics_root.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(metrics_root / "summary_by_variant.csv", index=False, encoding="utf-8-sig")

    per_sequence = []
    for variant in args.variants:
        file = metrics_root / variant / "per_sequence_metrics.csv"
        if file.exists():
            df = pd.read_csv(file)
            df["variant"] = variant
            per_sequence.append(df)
    if per_sequence:
        pd.concat(per_sequence, ignore_index=True).to_csv(metrics_root / "per_sequence_metrics_all.csv", index=False, encoding="utf-8-sig")

    write_iou_curves(results_root, gt_dir, args.variants, args.sequences[0], metrics_root / f"{args.sequences[0]}_iou_curves.csv")
    seq_table = pd.DataFrame({"sequence": args.sequences, "reason": ["fast trajectory prompt stress", "low event density", "fast motion", "high dynamic range", "similar or multiple objects"][: len(args.sequences)]})
    seq_table.to_csv(metrics_root / "selected_sequences.csv", index=False, encoding="utf-8-sig")
    print(summary_df.to_json(orient="records", force_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
