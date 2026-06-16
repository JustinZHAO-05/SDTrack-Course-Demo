from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


PAPER_ROWS = {
    "FE108 SDTrack-Tiny-1x4": {"paper_auc": 59.0, "paper_pr20": 91.3},
    "VisEvent SDTrack-Tiny-1x4": {"paper_auc": 35.6, "paper_pr20": 49.2},
}


def load_summary(path: Path) -> dict[str, float | int | str] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def first_existing_summary(*paths: Path) -> dict[str, float | int | str] | None:
    for path in paths:
        summary = load_summary(path)
        if summary is not None:
            return summary
    return None


def pct(value: float | int | None) -> float | None:
    if value is None:
        return None
    return round(float(value) * 100.0, 2)


def first_prediction_files(path: Path, repo: Path, limit: int = 12) -> list[str]:
    if not path.exists():
        return []
    files = []
    for file in sorted(path.glob("*.txt")):
        if file.stem.endswith(("_time", "_all_boxes", "_all_scores")):
            continue
        try:
            files.append(file.relative_to(repo).as_posix())
        except ValueError:
            files.append(file.as_posix())
        if len(files) >= limit:
            break
    return files


def tail_success_lines(path: Path, limit: int = 28) -> list[str]:
    if not path.exists():
        return []
    lines = []
    text = ""
    for encoding in ("utf-8", "utf-16"):
        try:
            text = path.read_text(encoding=encoding)
            break
        except UnicodeError:
            continue
    if not text:
        text = path.read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines():
        if any(token in line for token in ["Evaluating", "Tracker:", "FPS:", "Done,", "[returncode]", "Sequence:"]):
            cleaned = line.strip()
            if cleaned:
                lines.append(cleaned)
    return lines[-limit:]


def write_tex_table(df: pd.DataFrame, out: Path) -> None:
    rows = [
        "\\begin{tabular}{lrrrrrr}",
        "\\toprule",
        "数据与方法 & 论文AUC & 论文PR20 & 公开预测框AUC & 公开预测框PR20 & 本机推理AUC & 本机推理PR20\\\\",
        "\\midrule",
    ]
    for _, row in df.iterrows():
        values = []
        for col in ["paper_auc", "paper_pr20", "public_auc", "public_pr20", "local_auc", "local_pr20"]:
            values.append("--" if pd.isna(row[col]) else f"{float(row[col]):.2f}")
        rows.append(f"{row['setting']} & " + " & ".join(values) + "\\\\")
    rows.extend(["\\bottomrule", "\\end{tabular}"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(rows), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build sanitized reproduction evidence tables for the report.")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    out = repo / "outputs" / "tables"
    out.mkdir(parents=True, exist_ok=True)

    public_fe = first_existing_summary(
        repo / "outputs" / "metrics" / "fe108_official_methods" / "sdtrack_tiny" / "summary.json",
        repo / "outputs" / "metrics" / "fe108_official_methods" / "SDTrack-tiny" / "summary.json",
    )
    local_fe = load_summary(repo / "outputs" / "metrics" / "fe108_local_official_tiny" / "summary.json")
    public_vis = first_existing_summary(
        repo / "outputs" / "metrics" / "visevent_official_methods" / "sdtrack_tiny" / "summary.json",
        repo / "outputs" / "metrics" / "visevent_official_methods" / "SDTrack-tiny" / "summary.json",
    )
    local_vis = load_summary(repo / "outputs" / "metrics" / "visevent_local_official_tiny" / "summary.json")

    rows = []
    for setting, public_summary, local_summary in [
        ("FE108 SDTrack-Tiny-1x4", public_fe, local_fe),
        ("VisEvent SDTrack-Tiny-1x4", public_vis, local_vis),
    ]:
        paper = PAPER_ROWS[setting]
        rows.append(
            {
                "setting": setting,
                "paper_auc": paper["paper_auc"],
                "paper_pr20": paper["paper_pr20"],
                "public_auc": pct(public_summary.get("auc_micro")) if public_summary else None,
                "public_pr20": pct(public_summary.get("pr20_micro")) if public_summary else None,
                "local_auc": pct(local_summary.get("auc_micro")) if local_summary else None,
                "local_pr20": pct(local_summary.get("pr20_micro")) if local_summary else None,
                "local_sequences": local_summary.get("sequences") if local_summary else None,
                "local_frames": local_summary.get("frames") if local_summary else None,
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(out / "official_reproduction_comparison.csv", index=False, encoding="utf-8-sig")
    write_tex_table(df, out / "official_reproduction_comparison.tex")

    pred_files = first_prediction_files(repo / "outputs" / "test" / "tracking_results" / "SDTrack" / "SDTrack-tiny-fe108", repo)
    (out / "local_prediction_files.txt").write_text("\n".join(pred_files), encoding="utf-8")

    log_lines = tail_success_lines(repo / "outputs" / "logs" / "official_fe108_test.log")
    (out / "official_fe108_test_excerpt.txt").write_text("\n".join(log_lines), encoding="utf-8")

    env = load_summary(repo / "outputs" / "logs" / "environment_report.json") or {}
    env_lines = []
    commands = env.get("commands", {}) if isinstance(env, dict) else {}
    for name in ["torch", "nvidia-smi"]:
        item = commands.get(name, {}) if isinstance(commands, dict) else {}
        stdout = str(item.get("stdout", "")).splitlines()
        if stdout:
            env_lines.append(f"{name}: {stdout[0]}")
            if len(stdout) > 1 and name == "torch":
                env_lines.append(f"device: {stdout[1]}")
    (out / "environment_excerpt.txt").write_text("\n".join(env_lines), encoding="utf-8")
    print(df.to_json(orient="records", force_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
