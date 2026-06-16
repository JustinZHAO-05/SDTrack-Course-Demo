from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


COLORS = {
    "baseline": "#4C78A8",
    "zero": "#9AA3AA",
    "weak": "#72B7B2",
    "fixed1": "#54A24B",
    "strong": "#F58518",
    "adaptive": "#B279A2",
    "adaptive_smooth": "#E45756",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize ATR-GTP transform logs.")
    parser.add_argument("--log", default="outputs/gtp_ablation/atr_gtp_transform_log.csv")
    parser.add_argument("--out-fig", default="outputs/figures/atr_gtp_transform_stats.png")
    parser.add_argument("--out-table", default="outputs/tables/atr_gtp_transform_summary.csv")
    args = parser.parse_args()

    log_path = Path(args.log)
    if not log_path.exists():
        raise FileNotFoundError(log_path)

    df = pd.read_csv(log_path)
    order = ["baseline", "zero", "weak", "fixed1", "strong", "adaptive", "adaptive_smooth"]
    df["variant"] = pd.Categorical(df["variant"], categories=order, ordered=True)
    summary = (
        df.groupby("variant", observed=False)
        .agg(
            frames=("file", "count"),
            density_mean=("event_density", "mean"),
            beta_mean=("beta", "mean"),
            beta_std=("beta", "std"),
            beta_min=("beta", "min"),
            beta_max=("beta", "max"),
        )
        .reset_index()
    )
    summary["trajectory_energy_proxy"] = summary["beta_mean"] ** 2
    summary["relative_to_baseline"] = summary["trajectory_energy_proxy"] / float(
        summary.loc[summary["variant"].astype(str) == "baseline", "trajectory_energy_proxy"].iloc[0]
    )

    out_table = Path(args.out_table)
    out_table.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out_table, index=False, encoding="utf-8-sig")

    out_fig = Path(args.out_fig)
    out_fig.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 3.9), facecolor="#FBFAF6")
    colors = [COLORS[str(v)] for v in summary["variant"]]
    axes[0].bar(summary["variant"].astype(str), summary["beta_mean"], yerr=summary["beta_std"].fillna(0), color=colors, alpha=0.9)
    axes[0].axhline(1.0, color="#66717C", linestyle="--", linewidth=1.0)
    axes[0].set_title("ATR-GTP beta statistics on real GTP frames", fontsize=12, weight="bold")
    axes[0].set_ylabel("beta")
    axes[0].tick_params(axis="x", rotation=28, labelsize=8)
    axes[0].grid(axis="y", linestyle="--", alpha=0.3)

    axes[1].bar(summary["variant"].astype(str), summary["relative_to_baseline"], color=colors, alpha=0.9)
    axes[1].axhline(1.0, color="#66717C", linestyle="--", linewidth=1.0)
    axes[1].set_title("Trajectory-channel energy proxy", fontsize=12, weight="bold")
    axes[1].set_ylabel(r"$\mathbb{E}[\beta^2]$ relative to baseline")
    axes[1].tick_params(axis="x", rotation=28, labelsize=8)
    axes[1].grid(axis="y", linestyle="--", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_fig, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_table} and {out_fig}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
