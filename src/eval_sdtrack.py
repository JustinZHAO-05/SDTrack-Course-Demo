from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .metrics import (
    compute_sequence_metrics,
    load_vector,
    load_xywh,
    normalized_precision_curve,
    pair_prediction_and_gt,
    precision_curve,
    success_curve,
    weighted_average,
)


def configure_matplotlib() -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 160
    plt.rcParams["savefig.dpi"] = 240


def plot_curve(x: np.ndarray, y: np.ndarray, title: str, xlabel: str, ylabel: str, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.plot(x, y, color="#0B5CAD", linewidth=2.4)
    ax.fill_between(x, y, 0, color="#8CC5FF", alpha=0.25)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.45)
    ax.set_ylim(0, 1.02)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def category_tags(sequence: str) -> list[str]:
    name = sequence.lower()
    tags = ["all"]
    if "low" in name:
        tags.append("low_event_density")
    if "hdr" in name:
        tags.append("high_dynamic_range")
    if "motion" in name:
        tags.append("fast_motion")
    if "mul" in name:
        tags.append("similar_or_multiple_objects")
    if any(token in name for token in ["giraffe", "whale", "elephant", "tower"]):
        tags.append("large_or_deformable_object")
    if any(token in name for token in ["cup", "bottle", "box"]):
        tags.append("small_rigid_object")
    return tags


def load_valid_mask(absent_dir: str | None, sequence: str, n: int) -> np.ndarray | None:
    base_valid = np.ones(n, dtype=bool)
    if absent_dir:
        absent_file = Path(absent_dir) / f"{sequence}.txt"
        absent = load_vector(absent_file)
        if len(absent):
            base_valid[: min(n, len(absent))] &= absent[: min(n, len(absent))] <= 0
            return base_valid
    return None


def failure_label(pred_xywh: np.ndarray, gt_xywh: np.ndarray, iou: float, center_error: float) -> str:
    pw, ph = max(float(pred_xywh[2]), 1e-6), max(float(pred_xywh[3]), 1e-6)
    gw, gh = max(float(gt_xywh[2]), 1e-6), max(float(gt_xywh[3]), 1e-6)
    scale_gap = max(pw * ph, gw * gh) / max(min(pw * ph, gw * gh), 1e-6)
    if iou < 0.05 and center_error > 50:
        return "target_lost_or_background_absorption"
    if center_error > 20 and scale_gap < 1.8:
        return "center_drift"
    if scale_gap >= 1.8:
        return "scale_mismatch"
    if iou < 0.30:
        return "partial_overlap_degradation"
    return "borderline_localization"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate SDTrack xywh tracking outputs.")
    parser.add_argument("--pred", required=True, help="Prediction txt file or directory.")
    parser.add_argument("--gt", required=True, help="Ground-truth txt file or directory.")
    parser.add_argument("--out", default="outputs/metrics", help="Output directory.")
    parser.add_argument("--tracker-name", default="SDTrack-Tiny-1x4", help="Tracker label for reports.")
    parser.add_argument("--absent-dir", default="", help="Optional directory containing 0/1 absent flags; frames with absent=1 are ignored.")
    args = parser.parse_args()

    configure_matplotlib()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    pairs = pair_prediction_and_gt(args.pred, args.gt)
    if not pairs:
        raise SystemExit(f"No matched prediction/ground-truth txt files found: pred={args.pred} gt={args.gt}")

    rows = []
    all_ious = []
    all_errors = []
    all_norm_errors = []
    failures = []
    for name, pred_file, gt_file in pairs:
        pred = load_xywh(pred_file)
        gt = load_xywh(gt_file)
        valid = load_valid_mask(args.absent_dir or None, name, min(len(pred), len(gt)))
        metrics, arrays = compute_sequence_metrics(name, pred, gt, valid)
        row = asdict(metrics)
        row["category_tags"] = ";".join(category_tags(name))
        rows.append(row)
        all_ious.append(arrays["iou"])
        all_errors.append(arrays["center_error"])
        all_norm_errors.append(arrays["norm_center_error"])
        if len(arrays["iou"]):
            worst = np.argsort(arrays["iou"])[: min(10, len(arrays["iou"]))]
            for idx in worst:
                failures.append(
                    {
                        "sequence": name,
                        "frame_index": int(idx),
                        "iou": float(arrays["iou"][idx]),
                        "center_error": float(arrays["center_error"][idx]),
                        "failure_type": failure_label(arrays["pred"][idx], arrays["gt"][idx], float(arrays["iou"][idx]), float(arrays["center_error"][idx])),
                        "pred_xywh": arrays["pred"][idx].round(3).tolist(),
                        "gt_xywh": arrays["gt"][idx].round(3).tolist(),
                    }
                )

    df = pd.DataFrame(rows).sort_values(["auc", "pr20"], ascending=[True, True])
    df.to_csv(out / "per_sequence_metrics.csv", index=False, encoding="utf-8-sig")
    attr_rows = []
    for tag in sorted({tag for tags in df["category_tags"] for tag in str(tags).split(";") if tag}):
        sub = df[df["category_tags"].str.contains(tag, regex=False, na=False)]
        if len(sub):
            attr_rows.append(
                {
                    "attribute": tag,
                    "sequences": int(len(sub)),
                    "frames": int(sub["frames"].sum()),
                    "auc_weighted": weighted_average((row["auc"], row["frames"]) for _, row in sub.iterrows()),
                    "pr20_weighted": weighted_average((row["pr20"], row["frames"]) for _, row in sub.iterrows()),
                    "norm_precision_020_weighted": weighted_average((row["norm_precision_020"], row["frames"]) for _, row in sub.iterrows()),
                    "mean_failure_rate_iou_010": weighted_average((row["failure_rate_iou_010"], row["frames"]) for _, row in sub.iterrows()),
                }
            )
    pd.DataFrame(attr_rows).sort_values("auc_weighted", ascending=False).to_csv(out / "attribute_metrics.csv", index=False, encoding="utf-8-sig")

    ious = np.concatenate(all_ious) if all_ious else np.array([])
    errors = np.concatenate(all_errors) if all_errors else np.array([])
    norm_errors = np.concatenate(all_norm_errors) if all_norm_errors else np.array([])
    s_thr, s_curve, auc = success_curve(ious)
    p_thr, p_curve, pr20 = precision_curve(errors)
    np_thr, np_curve, norm_precision_020 = normalized_precision_curve(norm_errors)
    summary = {
        "tracker": args.tracker_name,
        "sequences": len(rows),
        "frames": int(sum(row["frames"] for row in rows)),
        "auc_micro": float(auc),
        "pr20_micro": float(pr20),
        "norm_precision_020_micro": float(norm_precision_020),
        "auc_sequence_weighted": weighted_average((row["auc"], row["frames"]) for row in rows),
        "pr20_sequence_weighted": weighted_average((row["pr20"], row["frames"]) for row in rows),
        "norm_precision_020_sequence_weighted": weighted_average((row["norm_precision_020"], row["frames"]) for row in rows),
        "mean_iou": float(ious.mean()) if len(ious) else 0.0,
        "mean_center_error": float(errors.mean()) if len(errors) else 0.0,
        "absent_filter": bool(args.absent_dir),
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "failure_cases.json").write_text(
        json.dumps(sorted(failures, key=lambda x: (x["iou"], -x["center_error"]))[:50], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    pd.DataFrame({"threshold": s_thr, "success": s_curve}).to_csv(out / "success_curve.csv", index=False)
    pd.DataFrame({"threshold": p_thr, "precision": p_curve}).to_csv(out / "precision_curve.csv", index=False)
    pd.DataFrame({"threshold": np_thr, "normalized_precision": np_curve}).to_csv(out / "normalized_precision_curve.csv", index=False)
    plot_curve(s_thr, s_curve, f"{args.tracker_name} Success Plot (AUC={auc:.3f})", "IoU threshold", "Success rate", out / "success_plot.png")
    plot_curve(p_thr, p_curve, f"{args.tracker_name} Precision Plot (PR20={pr20:.3f})", "Center error threshold / px", "Precision", out / "precision_plot.png")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
