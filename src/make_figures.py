from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, Rectangle

from .metrics import compute_sequence_metrics, load_xywh, pair_prediction_and_gt


PALETTE = {
    "ink": "#102033",
    "muted": "#5E6A75",
    "blue": "#1E5AA7",
    "cyan": "#1B9AAA",
    "red": "#C94141",
    "green": "#2E8B57",
    "gold": "#C8911F",
    "purple": "#7A4EA3",
    "paper": "#FBFAF6",
    "panel": "#FFFFFF",
    "line": "#C9D4E2",
    "gray": "#E9EEF5",
}


def configure_matplotlib() -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 160
    plt.rcParams["savefig.dpi"] = 260


def save(fig: plt.Figure, out: Path, name: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=0.6)
    fig.savefig(out / f"{name}.png", bbox_inches="tight")
    fig.savefig(out / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def box(ax, xy, wh, text, fc="#FFFFFF", ec=None, color=None, size=10, weight="normal"):
    ec = ec or PALETTE["line"]
    color = color or PALETTE["ink"]
    rect = Rectangle(xy, wh[0], wh[1], facecolor=fc, edgecolor=ec, linewidth=1.5)
    ax.add_patch(rect)
    ax.text(xy[0] + wh[0] / 2, xy[1] + wh[1] / 2, text, ha="center", va="center", fontsize=size, color=color, weight=weight)
    return rect


def arrow(ax, start, end, color=None, lw=1.6, scale=12):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=scale, linewidth=lw, color=color or PALETTE["muted"]))


def write_tables(out_tables: Path, benchmark: pd.DataFrame) -> None:
    out_tables.mkdir(parents=True, exist_ok=True)
    benchmark.to_csv(out_tables / "paper_table1_event_benchmark.csv", index=False, encoding="utf-8-sig")
    rec_path = Path("outputs/metrics/fe108_official_methods/summary_all_trackers.csv")
    if rec_path.exists():
        rec = pd.read_csv(rec_path).sort_values("auc_micro", ascending=False)
        rec.to_csv(out_tables / "fe108_recomputed_all_trackers.csv", index=False, encoding="utf-8-sig")
        top = rec.head(8).copy()
        top["AUC(%)"] = top["auc_micro"] * 100
        top["PR20(%)"] = top["pr20_micro"] * 100
        top[["tracker", "sequences", "frames", "AUC(%)", "PR20(%)"]].to_csv(out_tables / "fe108_top8_table.csv", index=False, encoding="utf-8-sig")
    vis_path = Path("outputs/metrics/visevent_official_methods/summary_all_trackers.csv")
    if vis_path.exists():
        vis = pd.read_csv(vis_path).sort_values("auc_micro", ascending=False)
        vis.to_csv(out_tables / "visevent_recomputed_all_trackers.csv", index=False, encoding="utf-8-sig")


def event_camera_principle(out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 3.9), facecolor=PALETTE["paper"])
    ax.set_axis_off()
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    box(ax, (0.45, 2.55), (2.25, 1.35), "Frame\nCamera", "#E8F2FF", PALETTE["blue"], size=13, weight="bold")
    for i in range(4):
        box(ax, (3.25 + i * 0.46, 2.68), (0.36, 1.05), "", "#FFFFFF", PALETTE["blue"])
    ax.text(3.23, 2.25, "固定帧率", fontsize=10, color=PALETTE["muted"])
    box(ax, (0.45, 0.95), (2.25, 1.35), "Event\nCamera", "#FFF2D6", PALETTE["gold"], size=13, weight="bold")
    rng = np.random.default_rng(4)
    pts = rng.normal(size=(90, 2))
    pts[:, 0] = 3.9 + pts[:, 0] * 0.48
    pts[:, 1] = 1.6 + pts[:, 1] * 0.36
    colors = np.where(rng.random(90) > 0.5, PALETTE["red"], PALETTE["blue"])
    ax.scatter(pts[:, 0], pts[:, 1], s=10, c=colors, alpha=0.8)
    ax.text(3.22, 0.62, r"$e_k=(x_k,y_k,t_k,p_k)$", fontsize=12, color=PALETTE["ink"])
    box(ax, (6.45, 1.35), (2.6, 2.15), "Tracking\nInput", "#FFFFFF", PALETTE["ink"], size=15, weight="bold")
    arrow(ax, (2.7, 3.22), (3.25, 3.22))
    arrow(ax, (2.7, 1.62), (3.25, 1.62))
    arrow(ax, (5.35, 2.45), (6.45, 2.45), PALETTE["ink"], 2.0)
    ax.text(0.45, 4.48, "事件相机记录亮度变化，天然形成稀疏异步流", fontsize=14, weight="bold", color=PALETTE["ink"])
    save(fig, out, "event_camera_principle")


def gtp_diagram(out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.1), facecolor=PALETTE["paper"])
    ax.set_axis_off()
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.5)
    box(ax, (0.35, 2.15), (1.85, 1.15), "Event\nStream", "#E8F2FF", PALETTE["blue"], size=12, weight="bold")
    branches = [
        ("$C^+$\npositive", 3.05, 4.05, "#E6F4EA", PALETTE["green"]),
        ("$C^-$\nnegative", 3.05, 2.65, "#FDECEC", PALETTE["red"]),
        ("$C^{traj}$\ntrajectory", 3.05, 1.25, "#FFF3D7", PALETTE["gold"]),
    ]
    for label, x, y, fc, ec in branches:
        box(ax, (x, y), (2.05, 0.78), label, fc, ec, size=11, weight="bold")
        arrow(ax, (2.2, 2.72), (3.05, y + 0.39))
    box(ax, (6.55, 2.25), (2.6, 1.0), "3-channel\nGTP image", "#FFFFFF", PALETTE["ink"], size=13, weight="bold")
    for _, _, y, _, _ in branches:
        arrow(ax, (5.1, y + 0.39), (6.55, 2.75), PALETTE["ink"], 1.5)
    ax.text(0.5, 4.92, "Global Trajectory Prompt", fontsize=15, weight="bold", color=PALETTE["ink"])
    ax.text(0.5, 0.38, r"$h_i^3=\beta h_{i-1}^3+\alpha\sum C(h_{i-1}^j,h_i^j)$", fontsize=13, color=PALETTE["ink"])
    save(fig, out, "gtp_channels")


def pipeline_diagram(out: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.6, 4.25), facecolor=PALETTE["paper"])
    ax.set_axis_off()
    ax.set_xlim(0, 12.4)
    ax.set_ylim(0, 5.6)
    nodes = [
        ("Template\nEvents", 0.35, 3.65, "#E8F2FF", PALETTE["blue"]),
        ("Search\nEvents", 0.35, 1.85, "#E8F2FF", PALETTE["blue"]),
        ("GTP", 2.15, 2.75, "#FFF3D7", PALETTE["gold"]),
        ("IPL\nJoint", 3.75, 2.75, "#F0E8FF", PALETTE["purple"]),
        ("SNN\nConv", 5.35, 2.75, "#E6F4EA", PALETTE["green"]),
        ("Restore\nTokenize", 6.95, 2.75, "#FFFFFF", PALETTE["line"]),
        ("SNN\nTransformer", 8.65, 2.75, "#E8F2FF", PALETTE["blue"]),
        ("SNN\nHead", 10.65, 2.75, "#FDECEC", PALETTE["red"]),
    ]
    for text, x, y, fc, ec in nodes:
        box(ax, (x, y - 0.42), (1.28, 0.84), text, fc, ec, size=9.5, weight="bold")
    for start, end in [
        ((1.63, 4.07), (2.15, 3.12)),
        ((1.63, 2.27), (2.15, 2.95)),
        ((3.43, 3.17), (3.75, 3.17)),
        ((5.03, 3.17), (5.35, 3.17)),
        ((6.63, 3.17), (6.95, 3.17)),
        ((8.23, 3.17), (8.65, 3.17)),
        ((9.93, 3.17), (10.65, 3.17)),
        ((11.93, 3.17), (12.25, 3.17)),
    ]:
        arrow(ax, start, end, scale=10)
    ax.text(12.26, 3.17, "bbox", ha="left", va="center", fontsize=10, color=PALETTE["ink"], weight="bold")
    ax.text(0.35, 5.0, "SDTrack pipeline 分解图", fontsize=15, weight="bold", color=PALETTE["ink"])
    save(fig, out, "sdtrack_pipeline")


def ilif_diagram(out: Path) -> None:
    t = np.linspace(0, 10, 320)
    inputs = np.zeros_like(t)
    for s in [0.9, 1.7, 2.5, 4.7, 5.35, 5.95, 7.8, 8.45]:
        inputs += np.exp(-((t - s) ** 2) / 0.008)
    u = np.zeros_like(t)
    spikes = []
    threshold = 1.0
    for i in range(1, len(t)):
        u[i] = 0.962 * u[i - 1] + inputs[i] * 0.18
        if u[i] >= threshold:
            spikes.append(t[i])
            u[i] = 0.0
    fig, ax = plt.subplots(figsize=(7.2, 3.65), facecolor=PALETTE["paper"])
    ax.plot(t, u, color=PALETTE["blue"], lw=2.2, label=r"$U[t]$")
    ax.axhline(threshold, color=PALETTE["red"], ls="--", lw=1.4, label="threshold")
    for s in spikes:
        ax.vlines(s, 0, 1.15, color=PALETTE["green"], lw=1.1)
    ax.set_xlabel("time")
    ax.set_ylabel("membrane")
    ax.set_title("I-LIF neuron: integrate, fire, reset", fontsize=13, weight="bold")
    ax.legend(frameon=False, loc="upper right")
    ax.grid(True, ls="--", alpha=0.32)
    save(fig, out, "ilif_neuron")


def ipl_diagram(out: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.9, 4.0), facecolor=PALETTE["paper"])
    ax.set_axis_off()
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 5.4)
    box(ax, (0.6, 3.45), (1.45, 0.82), "Search\n$X$", "#E8F2FF", PALETTE["blue"], size=11, weight="bold")
    box(ax, (0.6, 1.35), (1.45, 0.82), "Template\n$Z$", "#E6F4EA", PALETTE["green"], size=11, weight="bold")
    box(ax, (3.5, 1.15), (3.05, 3.1), "", "#FFFFFF", PALETTE["ink"])
    cells = [
        ("$X$", 3.68, 2.75, "#E8F2FF", PALETTE["blue"]),
        ("$O_1$", 5.07, 2.75, "#F8FAFC", PALETTE["line"]),
        ("$O_2$", 3.68, 1.36, "#F8FAFC", PALETTE["line"]),
        ("$Z$", 5.07, 1.36, "#E6F4EA", PALETTE["green"]),
    ]
    for label, x, y, fc, ec in cells:
        box(ax, (x, y), (1.28, 1.28), label, fc, ec, size=14, weight="bold")
    arrow(ax, (2.05, 3.86), (3.68, 3.39))
    arrow(ax, (2.05, 1.76), (5.07, 2.0))
    ax.text(0.58, 4.8, r"IPL: $U=[[X,O_1],[O_2,Z]]$", fontsize=14, weight="bold", color=PALETTE["ink"])
    save(fig, out, "ipl_diagonal")


def attention_diagram(out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.1, 3.9), facecolor=PALETTE["paper"])
    ax.set_axis_off()
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.4)
    box(ax, (0.55, 2.2), (1.45, 0.86), "Spike\nTokens", "#E8F2FF", PALETTE["blue"], size=11, weight="bold")
    for i, label in enumerate(["$Q_s$", "$K_s$", "$V_s$"]):
        y = 3.85 - i * 1.12
        box(ax, (3.0, y), (1.05, 0.62), label, "#FFFFFF", PALETTE["line"], size=13, weight="bold")
        arrow(ax, (2.0, 2.63), (3.0, y + 0.31), scale=10)
    box(ax, (5.0, 2.08), (2.0, 1.08), "$Q_sK_s^T V_s$", "#FFF3D7", PALETTE["gold"], size=14, weight="bold")
    for y in [4.16, 3.04, 1.92]:
        arrow(ax, (4.05, y), (5.0, 2.62), PALETTE["ink"], scale=10)
    box(ax, (8.0, 2.2), (1.55, 0.86), "Target\nFeatures", "#E6F4EA", PALETTE["green"], size=11, weight="bold")
    arrow(ax, (7.0, 2.62), (8.0, 2.62), scale=10)
    ax.text(0.55, 4.78, "SNN Self-Attention", fontsize=15, weight="bold", color=PALETTE["ink"])
    save(fig, out, "snn_attention")


def atr_gtp_diagram(out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 3.85), facecolor=PALETTE["paper"])
    ax.set_axis_off()
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 5)
    nodes = [
        ("GTP\n$[C^+,C^-,C^{traj}]$", 0.35, 2.2, "#E8F2FF", PALETTE["blue"]),
        ("Density\n$E_t$", 2.95, 2.2, "#FFF3D7", PALETTE["gold"]),
        ("Adaptive\n$\\beta_t$", 5.55, 2.2, "#F0E8FF", PALETTE["purple"]),
        ("Reweight\n$\\beta_t C^{traj}$", 8.15, 2.2, "#E6F4EA", PALETTE["green"]),
    ]
    for text, x, y, fc, ec in nodes:
        box(ax, (x, y), (2.0, 0.9), text, fc, ec, size=11, weight="bold")
    for x in [2.35, 4.95, 7.55]:
        arrow(ax, (x, 2.65), (x + 0.6, 2.65), scale=10)
    ax.text(0.35, 4.35, "ATR-GTP input-side trajectory control", fontsize=15, weight="bold", color=PALETTE["ink"])
    ax.text(0.35, 0.78, r"$\beta_t=\mathrm{clip}(\beta_0\bar{E}/(E_t+\epsilon),\beta_{min},\beta_{max})$", fontsize=13, color=PALETTE["ink"])
    save(fig, out, "atr_gtp")


def energy_formula(out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 3.55), facecolor=PALETTE["paper"])
    ax.set_axis_off()
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    box(ax, (0.7, 2.55), (2.0, 0.95), "MAC\n4.6 pJ", "#FDECEC", PALETTE["red"], size=13, weight="bold")
    box(ax, (4.0, 2.55), (2.0, 0.95), "AC\n0.9 pJ", "#E6F4EA", PALETTE["green"], size=13, weight="bold")
    box(ax, (7.3, 2.55), (2.0, 0.95), "Spike\nrate", "#E8F2FF", PALETTE["blue"], size=13, weight="bold")
    arrow(ax, (2.7, 3.02), (4.0, 3.02), scale=10)
    arrow(ax, (6.0, 3.02), (7.3, 3.02), scale=10)
    ax.text(0.7, 4.38, "Theoretical energy accounting", fontsize=15, weight="bold", color=PALETTE["ink"])
    ax.text(0.7, 1.22, r"$E=T(E_{MAC}\sum FL^{conv}+E_{AC}\sum FL^{spike}fr+\sum FL^{SSA})$", fontsize=12.5)
    save(fig, out, "energy_formula")


def metric_curves(out: Path) -> None:
    x = np.linspace(0, 1, 101)
    curves = {
        "SDTrack-Tiny": np.clip(1 - x**1.85, 0, 1) * 0.93,
        "HiT-B": np.clip(1 - x**1.55, 0, 1) * 0.88,
        "STARK": np.clip(1 - x**1.50, 0, 1) * 0.90,
    }
    fig, ax = plt.subplots(figsize=(6.6, 3.8), facecolor=PALETTE["paper"])
    for label, y in curves.items():
        ax.plot(x, y, lw=2.1, label=label)
    ax.set_title("Success Plot: AUC is the mean success rate", fontsize=12.5, weight="bold")
    ax.set_xlabel("IoU threshold")
    ax.set_ylabel("success rate")
    ax.legend(frameon=False)
    ax.grid(True, ls="--", alpha=0.32)
    save(fig, out, "success_plot_explained")

    x = np.arange(0, 51)
    curves = {
        "SDTrack-Tiny": 1 - np.exp(-x / 6.0),
        "HiT-B": 0.96 * (1 - np.exp(-x / 7.2)),
        "STARK": 0.98 * (1 - np.exp(-x / 7.0)),
    }
    fig, ax = plt.subplots(figsize=(6.6, 3.8), facecolor=PALETTE["paper"])
    for label, y in curves.items():
        ax.plot(x, np.clip(y, 0, 1), lw=2.1, label=label)
    ax.axvline(20, color=PALETTE["red"], ls="--", lw=1.4)
    ax.text(21, 0.1, "PR20", color=PALETTE["red"], fontsize=10)
    ax.set_title("Precision Plot: center-error threshold curve", fontsize=12.5, weight="bold")
    ax.set_xlabel("center error threshold / px")
    ax.set_ylabel("precision")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(True, ls="--", alpha=0.32)
    save(fig, out, "precision_plot_explained")


def benchmark_charts(out: Path, table: Path) -> pd.DataFrame:
    df = pd.read_csv(table)
    subset = df.dropna(subset=["power_mj", "visevent_auc", "param_m"]).copy()
    subset["is_sdtrack"] = subset["method"].str.contains("SDTrack")
    fig, ax = plt.subplots(figsize=(7.2, 4.15), facecolor=PALETTE["paper"])
    sizes = np.clip(subset["param_m"].fillna(20), 14, 220) * 4.6
    colors = [PALETTE["red"] if x else PALETTE["blue"] for x in subset["is_sdtrack"]]
    ax.scatter(subset["visevent_auc"], subset["power_mj"], s=sizes, c=colors, alpha=0.82, edgecolor="white", linewidth=1.0)
    energy_label_offsets = {
        "SDTrack-Base-1x4": (8, 8),
        "SDTrack-Tiny-1x4": (8, -14),
        "HiT-B": (-50, -12),
        "SNNTrack": (7, -18),
        "STARK": (-46, 6),
        "ODTrack": (7, 7),
    }
    for _, row in subset.iterrows():
        method = str(row["method"])
        if row["is_sdtrack"] or method in {"HiT-B", "SNNTrack", "STARK", "ODTrack"}:
            dx, dy = energy_label_offsets.get(method, (5, 5))
            ax.annotate(
                method,
                (row["visevent_auc"], row["power_mj"]),
                xytext=(dx, dy),
                textcoords="offset points",
                fontsize=7.5,
                ha="right" if dx < 0 else "left",
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.72),
            )
    ax.set_xlabel("VisEvent AUC (%)")
    ax.set_ylabel("theoretical energy (mJ)")
    ax.set_title("Accuracy-energy-parameter frontier", fontsize=13, weight="bold")
    ax.grid(True, linestyle="--", alpha=0.35)
    save(fig, out, "benchmark_bubble")

    top = df[df["method"].str.contains("SDTrack|HiT-B|SNNTrack|STARK|SimTrack", regex=True)].dropna(subset=["fe108_auc"]).copy()
    fig, ax = plt.subplots(figsize=(7.2, 3.9), facecolor=PALETTE["paper"])
    x = np.arange(len(top))
    ax.bar(x - 0.18, top["fe108_auc"], width=0.36, label="FE108 AUC", color=PALETTE["blue"])
    ax.bar(x + 0.18, top["fe108_pr"], width=0.36, label="FE108 PR20", color=PALETTE["cyan"])
    ax.set_xticks(x)
    ax.set_xticklabels(top["method"], rotation=25, ha="right", fontsize=8)
    ax.set_ylim(30, 100)
    ax.set_ylabel("%")
    ax.set_title("FE108 paper metrics for representative trackers", fontsize=12.5, weight="bold")
    ax.legend(frameon=False, ncol=2)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    save(fig, out, "fe108_metric_bar")
    return df


def classify_failure(pred: np.ndarray, gt: np.ndarray, iou: float, center_error: float) -> str:
    pw, ph = max(float(pred[2]), 1e-6), max(float(pred[3]), 1e-6)
    gw, gh = max(float(gt[2]), 1e-6), max(float(gt[3]), 1e-6)
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


def failure_mode_counts(pred_root: Path, gt_root: Path) -> pd.Series:
    if not pred_root.exists() or not gt_root.exists():
        return pd.Series(dtype=int)
    counts: dict[str, int] = {}
    for name, pred_file, gt_file in pair_prediction_and_gt(pred_root, gt_root):
        pred = load_xywh(pred_file)
        gt = load_xywh(gt_file)
        _, arrays = compute_sequence_metrics(name, pred, gt)
        valid = (
            (arrays["gt"][:, 2] > 2)
            & (arrays["gt"][:, 3] > 2)
            & np.all(np.isfinite(arrays["gt"]), axis=1)
            & np.all(np.isfinite(arrays["pred"]), axis=1)
        )
        bad = valid & (arrays["iou"] < 0.5)
        for idx in np.where(bad)[0]:
            label = classify_failure(arrays["pred"][idx], arrays["gt"][idx], float(arrays["iou"][idx]), float(arrays["center_error"][idx]))
            counts[label] = counts.get(label, 0) + 1
    return pd.Series(counts, dtype=int)


def recomputed_charts(out: Path) -> None:
    rec_path = Path("outputs/metrics/fe108_official_methods/summary_all_trackers.csv")
    if rec_path.exists():
        rec = pd.read_csv(rec_path).sort_values("auc_micro", ascending=False).head(10).copy()
        fig, ax = plt.subplots(figsize=(7.2, 3.95), facecolor=PALETTE["paper"])
        y = np.arange(len(rec))
        colors = [PALETTE["red"] if "sdtrack" in str(name).lower() else PALETTE["blue"] for name in rec["tracker"]]
        ax.barh(y, rec["auc_micro"] * 100, color=colors, alpha=0.88)
        ax.set_yticks(y)
        ax.set_yticklabels(rec["tracker"], fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("AUC (%)")
        ax.set_title("FE108 independent recomputation from official boxes", fontsize=12.5, weight="bold")
        for idx, value in enumerate(rec["auc_micro"] * 100):
            ax.text(value + 0.25, idx, f"{value:.2f}", va="center", fontsize=8)
        ax.set_xlim(35, max(rec["auc_micro"] * 100) + 5)
        ax.grid(axis="x", linestyle="--", alpha=0.35)
        save(fig, out, "fe108_recomputed_auc")

        full = pd.read_csv(rec_path)
        fig, ax = plt.subplots(figsize=(6.4, 4.3), facecolor=PALETTE["paper"])
        ax.scatter(full["auc_micro"] * 100, full["pr20_micro"] * 100, s=70, color=PALETTE["blue"], alpha=0.78, edgecolor="white")
        scatter_label_offsets = {
            "sdtrack_base": (8, -16),
            "sdtrack_tiny": (-38, 11),
            "v3": (-18, -17),
            "simtrack": (-42, 8),
            "artrack": (7, -12),
        }
        for _, row in full.iterrows():
            tracker = str(row["tracker"])
            if "sdtrack" in tracker.lower() or tracker in {"v3", "simtrack", "artrack"}:
                dx, dy = scatter_label_offsets.get(tracker, (5, 5))
                ax.annotate(
                    tracker,
                    (row["auc_micro"] * 100, row["pr20_micro"] * 100),
                    xytext=(dx, dy),
                    textcoords="offset points",
                    fontsize=7.6,
                    ha="right" if dx < 0 else "left",
                    bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.72),
                )
        ax.set_xlabel("AUC (%)")
        ax.set_ylabel("PR20 (%)")
        ax.set_title("FE108 recomputed AUC-PR relation", fontsize=12.5, weight="bold")
        ax.grid(True, ls="--", alpha=0.32)
        save(fig, out, "fe108_auc_pr_scatter")

    attr_path = Path("outputs/metrics/fe108_official_methods/sdtrack_tiny/attribute_metrics.csv")
    if attr_path.exists():
        attr = pd.read_csv(attr_path)
        attr = attr[attr["attribute"] != "all"].sort_values("auc_weighted")
        fig, ax = plt.subplots(figsize=(7.1, 3.8), facecolor=PALETTE["paper"])
        y = np.arange(len(attr))
        ax.barh(y, attr["auc_weighted"] * 100, color=PALETTE["purple"], alpha=0.86)
        ax.set_yticks(y)
        ax.set_yticklabels(attr["attribute"], fontsize=8)
        ax.set_xlabel("AUC (%)")
        ax.set_title("SDTrack-Tiny FE108 attribute slices", fontsize=12.5, weight="bold")
        ax.grid(axis="x", linestyle="--", alpha=0.32)
        save(fig, out, "fe108_attribute_auc")

    pred_root = Path("outputs/test/tracking_results/SDTrack/SDTrack-tiny-fe108")
    gt_root = Path("data/official_results_E/FE108_eval/FE108/annos/gt_rect")
    failures_path = Path("outputs/metrics/fe108_official_methods/sdtrack_tiny/failure_cases.json")
    counts = failure_mode_counts(pred_root, gt_root)
    if counts.empty and failures_path.exists():
        cases = json.loads(failures_path.read_text(encoding="utf-8"))
        counts = pd.Series([case.get("failure_type", "unknown") for case in cases]).value_counts()
    if not counts.empty:
        label_map = {
            "target_lost_or_background_absorption": "目标丢失/背景吸附",
            "center_drift": "中心漂移",
            "scale_mismatch": "尺度失配",
            "partial_overlap_degradation": "局部重叠退化",
            "borderline_localization": "低重叠定位",
        }
        counts = counts.sort_values(ascending=True)
        labels = [label_map.get(str(idx), str(idx)) for idx in counts.index]
        total = float(counts.sum())
        fig, ax = plt.subplots(figsize=(7.2, 3.8), facecolor=PALETTE["paper"])
        y = np.arange(len(counts))
        colors = [PALETTE["blue"], PALETTE["gold"], PALETTE["red"], PALETTE["purple"], PALETTE["green"]][-len(counts) :]
        ax.barh(y, counts.values, color=colors, alpha=0.88, height=0.58)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlabel("有效失败帧数（IoU < 0.5）")
        ax.set_title("FE108 本机推理失败类型诊断", fontsize=12.5, weight="bold")
        for idx, value in enumerate(counts.values):
            pct = value / total * 100 if total else 0
            ax.text(value + max(counts.values) * 0.015, idx, f"{int(value)}  ({pct:.1f}%)", va="center", fontsize=8.5, color=PALETTE["ink"])
        ax.set_xlim(0, max(counts.values) * 1.18)
        ax.grid(axis="x", linestyle="--", alpha=0.28)
        save(fig, out, "failure_type_bar")

    vis_path = Path("outputs/metrics/visevent_official_methods/summary_all_trackers.csv")
    if vis_path.exists():
        vis = pd.read_csv(vis_path).sort_values("auc_micro", ascending=False).head(10)
        fig, ax = plt.subplots(figsize=(7.2, 3.95), facecolor=PALETTE["paper"])
        y = np.arange(len(vis))
        colors = [PALETTE["red"] if "sdtrack" in str(name).lower() else PALETTE["green"] for name in vis["tracker"]]
        ax.barh(y, vis["auc_micro"] * 100, color=colors, alpha=0.86)
        ax.set_yticks(y)
        ax.set_yticklabels(vis["tracker"], fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("AUC (%)")
        ax.set_title("VisEvent official boxes recomputed by Python evaluator", fontsize=12.5, weight="bold")
        ax.grid(axis="x", linestyle="--", alpha=0.32)
        save(fig, out, "visevent_recomputed_auc")


def atr_ablation_charts(out: Path) -> None:
    protocol = Path("outputs/gtp_ablation/atr_gtp_protocol.csv")
    if not protocol.exists():
        return
    proto = pd.read_csv(protocol)
    order = ["baseline", "zero", "weak", "fixed1", "strong", "adaptive", "adaptive_smooth"]
    proto["order"] = proto["variant"].apply(lambda x: order.index(x) if x in order else 99)
    proto = proto.sort_values("order")
    labels = proto["variant"].tolist()
    beta_values = []
    for _, row in proto.iterrows():
        if row["mode"] == "fixed":
            beta_values.append(float(row["beta"]))
        elif row["mode"] == "adaptive":
            beta_values.append(1.0)
        else:
            beta_values.append(1.0)
    fig, ax = plt.subplots(figsize=(7.2, 3.75), facecolor=PALETTE["paper"])
    x = np.arange(len(labels))
    colors = [PALETTE["blue"], PALETTE["red"], PALETTE["gold"], PALETTE["cyan"], PALETTE["purple"], PALETTE["green"], "#56738F"]
    ax.bar(x, beta_values, color=colors, alpha=0.84)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("nominal beta")
    ax.set_title("ATR-GTP seven-variant ablation protocol", fontsize=12.5, weight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.32)
    save(fig, out, "atr_ablation_protocol")

    density = np.linspace(0.2, 2.2, 140)
    raw = np.clip(1.0 / density, 0.6, 1.4)
    smooth = np.zeros_like(raw)
    smooth[0] = raw[0]
    for i in range(1, len(raw)):
        smooth[i] = 0.65 * smooth[i - 1] + 0.35 * raw[i]
    fig, ax = plt.subplots(figsize=(6.9, 3.75), facecolor=PALETTE["paper"])
    ax.plot(density, raw, color=PALETTE["green"], lw=2.2, label="adaptive")
    ax.plot(density, smooth, color=PALETTE["purple"], lw=2.2, label="adaptive_smooth")
    ax.axhline(1.0, color=PALETTE["muted"], ls="--", lw=1)
    ax.set_xlabel("relative event density")
    ax.set_ylabel(r"$\beta_t$")
    ax.set_title("Event-density control curve for trajectory channel", fontsize=12.5, weight="bold")
    ax.legend(frameon=False)
    ax.grid(True, ls="--", alpha=0.32)
    save(fig, out, "atr_beta_curve")

    tracker_summary = Path("outputs/metrics/atr_gtp_tracker/summary_by_variant.csv")
    if tracker_summary.exists():
        summary = pd.read_csv(tracker_summary)
        if {"variant", "auc_micro", "pr20_micro"}.issubset(summary.columns):
            summary["order"] = summary["variant"].apply(lambda x: order.index(x) if x in order else 99)
            summary = summary.sort_values("order")
            x = np.arange(len(summary))
            width = 0.36
            fig, ax = plt.subplots(figsize=(7.3, 3.95), facecolor=PALETTE["paper"])
            ax.bar(x - width / 2, summary["auc_micro"] * 100, width=width, color=PALETTE["blue"], label="AUC")
            ax.bar(x + width / 2, summary["pr20_micro"] * 100, width=width, color=PALETTE["green"], label="PR20")
            ax.set_xticks(x)
            ax.set_xticklabels(summary["variant"], rotation=22, ha="right", fontsize=8)
            ax.set_ylabel("score (%)")
            ax.set_title("Complete tracker inference on ATR-GTP variants", fontsize=12.5, weight="bold")
            ax.legend(frameon=False, ncol=2)
            ax.grid(axis="y", linestyle="--", alpha=0.32)
            save(fig, out, "atr_gtp_tracker_bar")

    per_sequence_path = Path("outputs/metrics/atr_gtp_tracker/per_sequence_metrics_all.csv")
    if per_sequence_path.exists():
        per_seq = pd.read_csv(per_sequence_path)
        if {"variant", "sequence", "auc"}.issubset(per_seq.columns):
            per_seq["variant_order"] = per_seq["variant"].apply(lambda x: order.index(x) if x in order else 99)
            pivot = per_seq.sort_values("variant_order").pivot_table(index="variant", columns="sequence", values="auc", aggfunc="mean")
            pivot = pivot.reindex([variant for variant in order if variant in pivot.index])
            fig, ax = plt.subplots(figsize=(7.0, 3.9), facecolor=PALETTE["paper"])
            im = ax.imshow(pivot.values * 100, cmap="YlGnBu", aspect="auto", vmin=max(0, np.nanmin(pivot.values * 100) - 2), vmax=min(100, np.nanmax(pivot.values * 100) + 2))
            ax.set_xticks(np.arange(len(pivot.columns)))
            ax.set_xticklabels(pivot.columns, rotation=25, ha="right", fontsize=7.5)
            ax.set_yticks(np.arange(len(pivot.index)))
            ax.set_yticklabels(pivot.index, fontsize=8)
            ax.set_title("Per-sequence AUC heatmap for ATR-GTP tracker runs", fontsize=12.5, weight="bold")
            for i in range(pivot.shape[0]):
                for j in range(pivot.shape[1]):
                    value = pivot.values[i, j] * 100
                    ax.text(j, i, f"{value:.1f}", ha="center", va="center", fontsize=7, color="#12202B")
            cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.035)
            cbar.set_label("AUC (%)")
            fig.tight_layout()
            save(fig, out, "atr_gtp_sequence_heatmap")

    curve_files = sorted(Path("outputs/metrics/atr_gtp_tracker").glob("*_iou_curves.csv"))
    if curve_files:
        curves = pd.read_csv(curve_files[0])
        if {"variant", "frame", "iou"}.issubset(curves.columns):
            fig, ax = plt.subplots(figsize=(7.2, 4.25), facecolor=PALETTE["paper"])
            for variant in [v for v in order if v in set(curves["variant"])]:
                sub = curves[curves["variant"] == variant].sort_values("frame")
                smoothed = sub["iou"].rolling(window=25, center=True, min_periods=1).mean()
                ax.plot(sub["frame"], smoothed, lw=2.0, label=variant)
            ax.set_xlabel("frame index")
            ax.set_ylabel("IoU")
            title_sequence = str(curves["sequence"].iloc[0]) if "sequence" in curves.columns and len(curves) else "sequence"
            ax.set_title(f"Smoothed IoU trajectory on {title_sequence}", fontsize=12.5, weight="bold")
            ax.legend(frameon=False, ncol=4, fontsize=7.2, loc="upper center", bbox_to_anchor=(0.5, -0.16))
            ax.grid(True, ls="--", alpha=0.32)
            ax.set_ylim(0, 1.02)
            fig.subplots_adjust(bottom=0.28)
            save(fig, out, "atr_gtp_iou_curve")


def run_all(out: Path, table: Path, tables_out: Path) -> None:
    configure_matplotlib()
    benchmark = benchmark_charts(out, table)
    write_tables(tables_out, benchmark)
    event_camera_principle(out)
    gtp_diagram(out)
    pipeline_diagram(out)
    ilif_diagram(out)
    ipl_diagram(out)
    attention_diagram(out)
    atr_gtp_diagram(out)
    metric_curves(out)
    energy_formula(out)
    recomputed_charts(out)
    atr_ablation_charts(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate SDTrack report and slide figures.")
    parser.add_argument("--out", default="outputs/figures")
    parser.add_argument("--table", default="data/official_event_benchmark.csv")
    parser.add_argument("--tables-out", default="outputs/tables")
    args = parser.parse_args()
    run_all(Path(args.out), Path(args.table), Path(args.tables_out))
    print(f"Generated figures in {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
