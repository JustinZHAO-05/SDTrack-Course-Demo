from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .eval_sdtrack import main as eval_main


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate every tracker directory in an official SDTrack result bundle.")
    parser.add_argument("--results-root", required=True, help="Directory containing *_tracking_result folders.")
    parser.add_argument("--gt", required=True, help="Ground-truth directory.")
    parser.add_argument("--out", default="outputs/metrics/fe108_official_methods")
    parser.add_argument("--absent-dir", default="", help="Optional absent annotation directory.")
    args = parser.parse_args()

    results_root = Path(args.results_root)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for tracker_dir in sorted([p for p in results_root.iterdir() if p.is_dir()]):
        tracker = tracker_dir.name.removesuffix("_tracking_result")
        tracker_out = out / tracker
        import sys

        old_argv = sys.argv
        sys.argv = [
            "eval_sdtrack",
            "--pred",
            str(tracker_dir),
            "--gt",
            args.gt,
            "--out",
            str(tracker_out),
            "--tracker-name",
            tracker,
        ]
        if args.absent_dir:
            sys.argv.extend(["--absent-dir", args.absent_dir])
        try:
            eval_main()
        finally:
            sys.argv = old_argv
        summary = json.loads((tracker_out / "summary.json").read_text(encoding="utf-8"))
        rows.append(summary)
    df = pd.DataFrame(rows).sort_values("auc_micro", ascending=False)
    df.to_csv(out / "summary_all_trackers.csv", index=False, encoding="utf-8-sig")
    print(df[["tracker", "auc_micro", "pr20_micro", "sequences", "frames"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
