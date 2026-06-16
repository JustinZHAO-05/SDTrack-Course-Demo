from __future__ import annotations

import argparse
import csv
import html
import json
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


VARIANTS = ["baseline", "adaptive_smooth"]
COLORS = {"baseline": "#2563AF", "adaptive_smooth": "#2E8B57"}
RECOMMENDED_SEQUENCES = {
    "bike_low": "默认演示；低事件密度，运行时间较短",
    "box_hdr": "高动态范围；适合观察亮度变化下的框稳定性",
    "star_mul222": "相似目标与干扰；适合展示错误吸附风险",
    "star_motion": "快速轨迹；适合展示运动场景，但耗时更长",
    "dog_motion": "快速运动与尺度变化；耗时较长",
    "box_low": "低照度；适合展示事件稀疏输入",
    "cup_low": "低照度小目标；适合展示目标尺度影响",
    "truck_hdr": "车辆与高动态范围；运行时间较短",
}


plt = None
np = None
pd = None
prepare_variant_dataset = None
compute_sequence_metrics = None
load_xywh = None
normalized_precision_curve = None
precision_curve = None
success_curve = None
build_sequence = None


def ensure_eval_dependencies() -> None:
    global np, pd, compute_sequence_metrics, load_xywh, normalized_precision_curve, precision_curve, success_curve
    if np is None or pd is None:
        import numpy as _np
        import pandas as _pd

        np = _np
        pd = _pd
    if compute_sequence_metrics is None:
        from .metrics import (
            compute_sequence_metrics as _compute_sequence_metrics,
            load_xywh as _load_xywh,
            normalized_precision_curve as _normalized_precision_curve,
            precision_curve as _precision_curve,
            success_curve as _success_curve,
        )

        compute_sequence_metrics = _compute_sequence_metrics
        load_xywh = _load_xywh
        normalized_precision_curve = _normalized_precision_curve
        precision_curve = _precision_curve
        success_curve = _success_curve


def ensure_plot_dependencies() -> None:
    global plt
    ensure_eval_dependencies()
    if plt is None:
        import matplotlib.pyplot as _plt

        plt = _plt


def ensure_visual_dependencies() -> None:
    global build_sequence
    if build_sequence is None:
        from .visualize_sequences import build_sequence as _build_sequence

        build_sequence = _build_sequence


def ensure_atr_dependencies() -> None:
    global prepare_variant_dataset
    if prepare_variant_dataset is None:
        from .atr_gtp_tracker_eval import prepare_variant_dataset as _prepare_variant_dataset

        prepare_variant_dataset = _prepare_variant_dataset


@dataclass
class DemoState:
    repo: Path
    out_dir: Path
    sequences: list[str]
    replay_only: bool
    no_browser: bool
    started_at: float = field(default_factory=time.time)
    status: str = "running"
    current_stage: str = "initializing"
    stages: list[dict[str, str]] = field(default_factory=list)
    environment: dict[str, str | int | bool] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)
    metrics: list[dict[str, str | int | float]] = field(default_factory=list)
    prediction_samples: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    error: str = ""

    @property
    def elapsed(self) -> float:
        return time.time() - self.started_at


def rel(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def rel_or_name(path: Path, base: Path) -> str:
    try:
        return rel(path, base)
    except Exception:
        return path.name


def split_sequence_args(values: list[str] | None) -> list[str]:
    if not values:
        return ["bike_low"]
    sequences: list[str] = []
    for value in values:
        for part in value.split(","):
            item = part.strip()
            if item and item not in sequences:
                sequences.append(item)
    return sequences or ["bike_low"]


def available_sequences(repo: Path) -> list[str]:
    names: set[str] = set()
    for root in [repo / "demo_assets" / "FE108" / "test", repo / "data" / "FE108" / "test"]:
        if root.exists():
            for path in root.iterdir():
                if (path / "inter1_stack_3008").exists():
                    names.add(path.name)
    return sorted(names)


def sequence_source_root(repo: Path, sequences: list[str]) -> Path:
    demo_root = repo / "demo_assets" / "FE108" / "test"
    if demo_root.exists() and all((demo_root / seq / "inter1_stack_3008").exists() for seq in sequences):
        return demo_root
    return repo / "data" / "FE108" / "test"


def sequence_gt_dir(repo: Path, sequences: list[str]) -> Path:
    demo_gt = repo / "demo_assets" / "FE108" / "annos" / "gt_rect"
    if demo_gt.exists() and all((demo_gt / f"{seq}.txt").exists() for seq in sequences):
        return demo_gt
    return repo / "data" / "official_results_E" / "FE108_eval" / "FE108" / "annos" / "gt_rect"


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_text_tail(path: Path, max_lines: int = 180) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return "\n".join(lines[-max_lines:])


def prediction_sample(path: Path, rows: int = 5) -> list[str]:
    if not path.exists():
        return []
    lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
    if len(lines) <= rows * 2:
        return lines
    return lines[:rows] + ["..."] + lines[-rows:]


def html_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = "\n".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def media_card(title: str, video_src: str, preview_src: str, full_src: str) -> str:
    if not (video_src or preview_src or full_src):
        return ""
    local_legend = ""
    if "输出框序列" in title:
        local_legend = """
        <div class="box-legend">
          <span><i class="legend-box gt-box"></i>红框：GT 真值框</span>
          <span><i class="legend-box base-box"></i>蓝框：原始模型 SDTrack-Tiny</span>
          <span><i class="legend-box atr-box"></i>绿框：改进后跟踪器 ATR-GTP</span>
        </div>
        """
    video_html = (
        f"""
        <video controls muted playsinline preload="metadata">
          <source src="{html.escape(video_src)}" type="video/mp4">
        </video>
        """
        if video_src
        else ""
    )
    preview_html = f'<img class="gif-preview" src="{html.escape(preview_src)}" alt="{html.escape(title)} GIF 预览">' if preview_src else ""
    links = []
    if video_src:
        links.append(f'<a href="{html.escape(video_src)}" target="_blank">浏览器 MP4</a>')
    if full_src and full_src != video_src:
        links.append(f'<a href="{html.escape(full_src)}" target="_blank">原始 MP4</a>')
    if preview_src:
        links.append(f'<a href="{html.escape(preview_src)}" target="_blank">GIF 预览</a>')
    link_html = f"<p class='media-links'>{' · '.join(links)}</p>" if links else ""
    return f"""
    <section class="panel">
      <h3>{html.escape(title)}</h3>
      {local_legend}
      {video_html}
      {preview_html}
      {link_html}
    </section>
    """


def render_dashboard(state: DemoState) -> None:
    out = state.out_dir
    index = out / "index.html"
    status_class = "done" if state.status == "complete" else "failed" if state.status == "failed" else "running"
    refresh = "" if state.status in {"complete", "failed"} else '<meta http-equiv="refresh" content="3">'

    stage_rows = [[s["name"], f'<span class="{s["status"]}">{s["status"]}</span>', html.escape(s.get("note", ""))] for s in state.stages]
    env_rows = [[html.escape(str(k)), html.escape(str(v))] for k, v in state.environment.items()]
    metric_rows = []
    for row in state.metrics:
        metric_rows.append(
            [
                html.escape(str(row.get("variant", ""))),
                str(row.get("sequences", "")),
                str(row.get("frames", "")),
                f"{float(row.get('auc_micro', 0)) * 100:.2f}",
                f"{float(row.get('pr20_micro', 0)) * 100:.2f}",
                f"{float(row.get('norm_precision_020_micro', 0)) * 100:.2f}",
                f"{float(row.get('mean_iou', 0)) * 100:.2f}",
                f"{float(row.get('mean_center_error', 0)):.2f}",
            ]
        )

    video_cards = []
    for sequence in state.sequences:
        manifest = state.outputs.get(f"{sequence}:manifest", "")
        cards = [
            media_card(
                "完整输入事件帧流",
                state.outputs.get(f"{sequence}:input_video", ""),
                state.outputs.get(f"{sequence}:input_preview", ""),
                state.outputs.get(f"{sequence}:input_full_video", ""),
            ),
            media_card(
                "输出框序列：GT / 原始模型 / 改进后跟踪器",
                state.outputs.get(f"{sequence}:output_video", ""),
                state.outputs.get(f"{sequence}:output_preview", ""),
                state.outputs.get(f"{sequence}:output_full_video", ""),
            ),
            media_card(
                "ATR-GTP 输入对比：原始 GTP / adaptive_smooth",
                state.outputs.get(f"{sequence}:atr_compare_video", ""),
                state.outputs.get(f"{sequence}:atr_compare_preview", ""),
                state.outputs.get(f"{sequence}:atr_compare_full_video", ""),
            ),
        ]
        video_cards.append(
            f"""
            <h2>序列：{html.escape(sequence)}</h2>
            <p class="muted">manifest: {html.escape(manifest)}</p>
            <div class="video-grid">{''.join(card for card in cards if card)}</div>
            """
        )

    pred_blocks = []
    for variant, seqs in state.prediction_samples.items():
        for sequence, lines in seqs.items():
            pred_blocks.append(
                f"""
                <section class="panel">
                  <h3>{html.escape(variant)} / {html.escape(sequence)} prediction 样例</h3>
                  <pre>{html.escape(chr(10).join(lines))}</pre>
                </section>
                """
            )

    charts = []
    for title, key in [("AUC/PR20 指标对比", "metrics_bar"), ("逐帧 IoU 曲线", "iou_curve")]:
        if state.outputs.get(key):
            charts.append(
                f"""
                <section class="panel">
                  <h3>{html.escape(title)}</h3>
                  <img src="{html.escape(state.outputs[key])}" alt="{html.escape(title)}">
                </section>
                """
            )

    mode_label = "回放已有结果" if state.replay_only else "现场实机运行"
    warning = (
        "<div class='banner replay'>ReplayOnly：本页面使用已有 prediction 与视频重新生成，不代表本次重新调用模型。</div>"
        if state.replay_only
        else "<div class='banner live'>Live：本页面由本次调用官方 test 脚本和 ATR-GTP 输入变体产生。</div>"
    )
    error = f"<pre class='error-box'>{html.escape(state.error)}</pre>" if state.error else ""
    log_tail = html.escape(read_text_tail(out / "logs" / "demo.log"))

    index.write_text(
        f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {refresh}
  <title>SDTrack 现场 Demo</title>
  <style>
    :root {{ --ink:#17202a; --muted:#5b6573; --line:#d5dde7; --paper:#f7f8fa; --panel:#ffffff; --blue:#2563AF; --green:#2E8B57; --red:#C84F4F; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family:"Microsoft YaHei", "Segoe UI", sans-serif; color:var(--ink); background:var(--paper); }}
    header {{ padding:18px 24px; border-bottom:1px solid var(--line); background:#fff; position:sticky; top:0; z-index:2; }}
    h1 {{ margin:0 0 8px; font-size:24px; }}
    h2 {{ margin:24px 0 10px; font-size:18px; }}
    h3 {{ margin:0 0 10px; font-size:14px; }}
    main {{ padding:18px 24px 32px; max-width:1500px; margin:0 auto; }}
    .topline {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; }}
    .pill {{ display:inline-flex; align-items:center; padding:4px 9px; border:1px solid var(--line); border-radius:6px; background:#fff; font-size:12px; }}
    .pill strong {{ margin-right:5px; }}
    .running {{ color:#b26a00; font-weight:700; }}
    .done {{ color:#1b7d45; font-weight:700; }}
    .failed {{ color:#b3261e; font-weight:700; }}
    .banner {{ margin:14px 0; padding:10px 12px; border-radius:6px; font-size:13px; }}
    .live {{ background:#e8f4ee; border:1px solid #b8ddc8; }}
    .replay {{ background:#fff4d6; border:1px solid #e2c766; }}
    .grid {{ display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:14px; }}
    .video-grid {{ display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:14px; }}
    .panel {{ background:var(--panel); border:1px solid var(--line); border-radius:6px; padding:12px; overflow:hidden; }}
    video, img {{ width:100%; display:block; border:1px solid var(--line); background:#000; }}
    .gif-preview {{ margin-top:8px; }}
    .media-links {{ margin:8px 0 0; font-size:12px; }}
    .media-links a {{ color:#245ea8; text-decoration:none; margin-right:8px; }}
    .media-links a:hover {{ text-decoration:underline; }}
    table {{ width:100%; border-collapse:collapse; font-size:12px; background:#fff; }}
    th, td {{ border-bottom:1px solid var(--line); padding:7px 8px; text-align:left; vertical-align:top; }}
    th {{ background:#eef2f7; font-weight:700; }}
    pre {{ margin:0; white-space:pre-wrap; word-break:break-word; font-size:11px; line-height:1.45; background:#0f1720; color:#e6edf3; padding:10px; border-radius:4px; max-height:340px; overflow:auto; }}
    .muted {{ color:var(--muted); font-size:12px; }}
    .legend span {{ display:inline-block; margin-right:16px; font-size:13px; }}
    .dot {{ width:12px; height:12px; border-radius:2px; margin-right:5px; vertical-align:-1px; }}
    .box-legend {{ display:flex; flex-wrap:wrap; gap:8px 12px; margin:0 0 8px; font-size:12px; color:var(--ink); }}
    .box-legend span {{ white-space:nowrap; }}
    .legend-box {{ display:inline-block; width:22px; height:13px; border:3px solid; margin-right:5px; vertical-align:-2px; background:transparent; }}
    .gt-box {{ border-color:var(--red); }}
    .base-box {{ border-color:var(--blue); }}
    .atr-box {{ border-color:var(--green); }}
    .error-box {{ background:#3b0a0a; color:#ffd7d7; }}
    @media (max-width: 1000px) {{ .grid, .video-grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>SDTrack 现场 Demo：原始模型复现与 ATR-GTP 改进推理</h1>
    <div class="topline">
      <span class="pill"><strong>模式</strong>{html.escape(mode_label)}</span>
      <span class="pill"><strong>状态</strong><span class="{status_class}">{html.escape(state.status)}</span></span>
      <span class="pill"><strong>当前阶段</strong>{html.escape(state.current_stage)}</span>
      <span class="pill"><strong>耗时</strong>{state.elapsed:.1f}s</span>
      <span class="pill"><strong>序列</strong>{html.escape(', '.join(state.sequences))}</span>
    </div>
  </header>
  <main>
    {warning}
    {error}
    <div class="legend">
      <span><i class="dot" style="background:var(--red)"></i>GT</span>
      <span><i class="dot" style="background:var(--blue)"></i>原始模型 SDTrack-Tiny</span>
      <span><i class="dot" style="background:var(--green)"></i>改进后跟踪器 ATR-GTP adaptive_smooth</span>
    </div>
    <section class="grid">
      <div class="panel"><h3>运行阶段</h3>{html_table(["阶段", "状态", "说明"], stage_rows)}</div>
      <div class="panel"><h3>环境与数据</h3>{html_table(["项目", "值"], env_rows)}</div>
    </section>
    <h2>指标对比</h2>
    <section class="panel">{html_table(["variant", "seq", "frames", "AUC(%)", "PR20(%)", "NP@0.2(%)", "mean IoU(%)", "center err(px)"], metric_rows) if metric_rows else "<p class='muted'>指标将在推理完成后显示。</p>"}</section>
    <div class="grid">{''.join(charts)}</div>
    {''.join(video_cards)}
    <h2>Prediction 文件样例</h2>
    <div class="grid">{''.join(pred_blocks) if pred_blocks else "<section class='panel'><p class='muted'>prediction 样例将在推理完成后显示。</p></section>"}</div>
    <h2>现场日志</h2>
    <pre>{log_tail}</pre>
  </main>
</body>
</html>
""",
        encoding="utf-8",
    )
    write_json(out / "state.json", state_to_json(state))


def state_to_json(state: DemoState) -> dict[str, object]:
    return {
        "status": state.status,
        "current_stage": state.current_stage,
        "elapsed_seconds": state.elapsed,
        "sequences": state.sequences,
        "replay_only": state.replay_only,
        "environment": state.environment,
        "outputs": state.outputs,
        "metrics": state.metrics,
        "error": state.error,
    }


def set_stage(state: DemoState, name: str, status: str, note: str = "") -> None:
    state.current_stage = name
    for stage in state.stages:
        if stage["name"] == name:
            stage["status"] = status
            stage["note"] = note
            break
    else:
        state.stages.append({"name": name, "status": status, "note": note})
    render_dashboard(state)


def log_line(state: DemoState, message: str) -> None:
    log = state.out_dir / "logs" / "demo.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")


def command_text(cmd: list[str]) -> str:
    return " ".join(f'"{x}"' if " " in x else x for x in cmd)


def make_browser_mp4(state: DemoState, source: Path) -> Path:
    """Return a browser-friendly H.264 MP4 when ffmpeg is available."""
    if not source.exists() or source.suffix.lower() != ".mp4":
        return source
    target = source.with_name(f"{source.stem}_browser.mp4")
    if target.exists() and target.stat().st_size > 2048:
        return target
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        log_line(state, f"ffmpeg not found; dashboard will link original MP4: {source.name}")
        return source
    cmd = [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(target),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    if result.returncode != 0 or not target.exists():
        log_line(state, f"ffmpeg H.264 transcode failed for {source.name}: {result.stdout.strip()}")
        return source
    return target


def run_process_live(state: DemoState, cmd: list[str], cwd: Path, env: dict[str, str], log_file: Path) -> None:
    log_line(state, f"$ {command_text(cmd)}")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("w", encoding="utf-8") as out, subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    ) as proc:
        last_render = 0.0
        assert proc.stdout is not None
        for line in proc.stdout:
            out.write(line)
            out.flush()
            with (state.out_dir / "logs" / "demo.log").open("a", encoding="utf-8") as demo:
                demo.write(line)
            if time.time() - last_render > 2.5:
                render_dashboard(state)
                last_render = time.time()
        returncode = proc.wait()
    log_line(state, f"[returncode] {returncode}")
    if returncode != 0:
        raise RuntimeError(f"command failed with return code {returncode}: {command_text(cmd)}")


def precheck(state: DemoState) -> dict[str, Path]:
    repo = state.repo
    python = repo / ".venv" / "Scripts" / "python.exe"
    if not python.exists():
        python = Path(sys.executable)
    official_root = repo / "external" / "SDTrack" / "SDTrack-Event"
    source_root = sequence_source_root(repo, state.sequences)
    data_root = source_root.parent
    checkpoint = repo / "outputs" / "checkpoints" / "train" / "SDTrack" / "SDTrack-tiny-fe108" / "SDTrack_ep0100.pth.tar"
    pretrained_weight = repo / "data" / "weights" / "SDTrack-tiny-1x4.pth"
    gt_dir = sequence_gt_dir(repo, state.sequences)

    missing: list[str] = []
    for path in [python, official_root / "tracking" / "test.py", source_root, checkpoint, pretrained_weight, gt_dir]:
        if not path.exists():
            missing.append(str(path))
    for sequence in state.sequences:
        if not (source_root / sequence / "inter1_stack_3008").exists():
            missing.append(str(source_root / sequence / "inter1_stack_3008"))
        if not (source_root / sequence / "groundtruth_rect.txt").exists():
            missing.append(str(source_root / sequence / "groundtruth_rect.txt"))
    if missing:
        raise FileNotFoundError("missing required demo resources:\n" + "\n".join(missing))

    torch_info = subprocess.run(
        [str(python), "-c", "import torch, json; print(json.dumps({'torch': torch.__version__, 'cuda': torch.cuda.is_available(), 'gpu': torch.cuda.get_device_name(0) if torch.cuda.is_available() else ''}, ensure_ascii=False))"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    try:
        info = json.loads(torch_info.stdout.strip().splitlines()[-1])
    except Exception:
        info = {"torch": "unknown", "cuda": False, "gpu": torch_info.stdout.strip()}
    if not state.replay_only and not info.get("cuda"):
        raise RuntimeError("CUDA is not available; live demo requires GPU. Use -ReplayOnly for emergency playback.")

    frame_counts = {}
    for sequence in state.sequences:
        frame_counts[sequence] = len(list((source_root / sequence / "inter1_stack_3008").glob("*.png")))
    demo_sequence_root = repo / "demo_assets" / "FE108" / "test"
    project_demo_sequences = sorted(path.name for path in demo_sequence_root.iterdir() if (path / "inter1_stack_3008").exists()) if demo_sequence_root.exists() else []
    available_now = available_sequences(repo)
    state.environment = {
        "python": rel_or_name(python, repo),
        "torch": str(info.get("torch", "")),
        "cuda_available": bool(info.get("cuda", False)),
        "gpu": str(info.get("gpu", "")),
        "checkpoint": "outputs/checkpoints/train/SDTrack/SDTrack-tiny-fe108/SDTrack_ep0100.pth.tar",
        "pretrained_weight": "data/weights/SDTrack-tiny-1x4.pth",
        "official_test_entry": "external/SDTrack/SDTrack-Event/tracking/test.py",
        "input_root": rel(source_root, repo),
        "gt_root": rel(gt_dir, repo),
        "frame_counts": ", ".join(f"{k}={v}" for k, v in frame_counts.items()),
        "project_demo_sequences": ", ".join(project_demo_sequences),
        "available_sequences": ", ".join(available_now),
        "output_dir": rel(state.out_dir, repo),
    }
    return {
        "python": python,
        "official_root": official_root,
        "source_root": source_root,
        "data_root": data_root,
        "checkpoint": checkpoint,
        "pretrained_weight": pretrained_weight,
        "gt_dir": gt_dir,
    }


def remove_existing_prediction(results_root: Path, sequence: str) -> None:
    pred_root = results_root / "SDTrack" / "SDTrack-tiny-fe108"
    for suffix in [".txt", "_time.txt", "_all_boxes.txt", "_all_scores.txt"]:
        path = pred_root / f"{sequence}{suffix}"
        if path.exists():
            path.unlink()


def run_tracker_sequence(state: DemoState, paths: dict[str, Path], dataset_root: Path, results_root: Path, variant: str, sequence: str) -> None:
    remove_existing_prediction(results_root, sequence)
    env = os.environ.copy()
    env["SDTRACK_EOTB_PATH"] = str(dataset_root)
    env["SDTRACK_RESULTS_PATH"] = str(results_root)
    env["SDTRACK_SAVE_DIR"] = str(state.repo / "outputs")
    env["SDTRACK_PRJ_DIR"] = str(paths["official_root"])
    env["SDTRACK_REPO_ROOT"] = str(state.repo)
    env["SDTRACK_RESULT_PLOT_PATH"] = str(state.out_dir / "result_plots")
    env["SDTRACK_SEGMENTATION_PATH"] = str(state.out_dir / "segmentation_results")
    env["SDTRACK_SEQUENCE_FILTER"] = sequence
    cmd = [
        str(paths["python"]),
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
    run_process_live(state, cmd, paths["official_root"], env, state.out_dir / "logs" / f"{variant}_{sequence}_test.log")
    pred = results_root / "SDTrack" / "SDTrack-tiny-fe108" / f"{sequence}.txt"
    if not pred.exists():
        raise FileNotFoundError(f"tracker completed but prediction file was not created: {pred}")


def collect_replay_predictions(state: DemoState, paths: dict[str, Path]) -> tuple[Path, Path, Path]:
    baseline_src = state.repo / "outputs" / "test" / "tracking_results" / "SDTrack" / "SDTrack-tiny-fe108"
    atr_src = state.repo / "outputs" / "atr_gtp_tracking" / "results" / "adaptive_smooth" / "SDTrack" / "SDTrack-tiny-fe108"
    atr_input_root = state.repo / "outputs" / "atr_gtp_tracking" / "datasets" / "adaptive_smooth"
    baseline_dst = state.out_dir / "results" / "baseline" / "SDTrack" / "SDTrack-tiny-fe108"
    atr_dst = state.out_dir / "results" / "adaptive_smooth" / "SDTrack" / "SDTrack-tiny-fe108"
    baseline_dst.mkdir(parents=True, exist_ok=True)
    atr_dst.mkdir(parents=True, exist_ok=True)
    for sequence in state.sequences:
        for src_root, dst_root in [(baseline_src, baseline_dst), (atr_src, atr_dst)]:
            for suffix in [".txt", "_time.txt"]:
                src = src_root / f"{sequence}{suffix}"
                if not src.exists():
                    raise FileNotFoundError(f"ReplayOnly missing existing prediction: {src}")
                shutil.copy2(src, dst_root / src.name)
    return baseline_dst, atr_dst, atr_input_root


def evaluate_demo(state: DemoState, baseline_pred_dir: Path, atr_pred_dir: Path, gt_dir: Path) -> None:
    ensure_eval_dependencies()
    rows = []
    all_iou_rows = []
    per_seq_rows = []
    for variant, pred_dir in [("baseline", baseline_pred_dir), ("adaptive_smooth", atr_pred_dir)]:
        all_ious = []
        all_errors = []
        all_norm_errors = []
        for sequence in state.sequences:
            pred = load_xywh(pred_dir / f"{sequence}.txt")
            gt = load_xywh(gt_dir / f"{sequence}.txt")
            metrics, arrays = compute_sequence_metrics(sequence, pred, gt)
            row = {"variant": variant, **metrics.__dict__}
            per_seq_rows.append(row)
            all_ious.append(arrays["iou"])
            all_errors.append(arrays["center_error"])
            all_norm_errors.append(arrays["norm_center_error"])
            for idx, iou in enumerate(arrays["iou"]):
                all_iou_rows.append({"variant": variant, "sequence": sequence, "frame": idx, "iou": float(iou)})
        ious = np.concatenate(all_ious) if all_ious else np.array([])
        errors = np.concatenate(all_errors) if all_errors else np.array([])
        norm_errors = np.concatenate(all_norm_errors) if all_norm_errors else np.array([])
        _, _, auc = success_curve(ious)
        _, _, pr20 = precision_curve(errors)
        _, _, norm_p = normalized_precision_curve(norm_errors)
        rows.append(
            {
                "variant": variant,
                "sequences": len(state.sequences),
                "frames": int(len(ious)),
                "auc_micro": float(auc),
                "pr20_micro": float(pr20),
                "norm_precision_020_micro": float(norm_p),
                "mean_iou": float(ious.mean()) if len(ious) else 0.0,
                "mean_center_error": float(errors.mean()) if len(errors) else 0.0,
            }
        )

    metrics_dir = state.out_dir / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(metrics_dir / "summary_by_variant.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(per_seq_rows).to_csv(metrics_dir / "per_sequence_metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(all_iou_rows).to_csv(metrics_dir / "iou_curves.csv", index=False, encoding="utf-8-sig")
    write_json(metrics_dir / "summary_by_variant.json", rows)
    state.metrics = rows

    samples: dict[str, dict[str, list[str]]] = {}
    for variant, pred_dir in [("baseline", baseline_pred_dir), ("adaptive_smooth", atr_pred_dir)]:
        samples[variant] = {}
        for sequence in state.sequences:
            samples[variant][sequence] = prediction_sample(pred_dir / f"{sequence}.txt")
    state.prediction_samples = samples


def plot_demo_figures(state: DemoState) -> None:
    ensure_plot_dependencies()
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    fig_dir = state.out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    summary = pd.DataFrame(state.metrics)
    if not summary.empty:
        x = np.arange(len(summary))
        width = 0.36
        fig, ax = plt.subplots(figsize=(7.4, 4.1), dpi=160)
        ax.bar(x - width / 2, summary["auc_micro"] * 100, width=width, color="#2563AF", label="AUC")
        ax.bar(x + width / 2, summary["pr20_micro"] * 100, width=width, color="#2E8B57", label="PR20")
        ax.set_xticks(x)
        ax.set_xticklabels(["原始模型" if v == "baseline" else "改进后跟踪器" for v in summary["variant"]])
        ax.set_ylabel("score (%)")
        ax.set_title("Live demo metric comparison")
        ax.grid(axis="y", linestyle="--", alpha=0.32)
        ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(fig_dir / "metrics_bar.png")
        plt.close(fig)
        state.outputs["metrics_bar"] = rel(fig_dir / "metrics_bar.png", state.out_dir)

    curves_path = state.out_dir / "metrics" / "iou_curves.csv"
    if curves_path.exists():
        curves = pd.read_csv(curves_path)
        sequence = state.sequences[0]
        fig, ax = plt.subplots(figsize=(8.0, 4.2), dpi=160)
        for variant in VARIANTS:
            sub = curves[(curves["variant"] == variant) & (curves["sequence"] == sequence)].sort_values("frame")
            if not sub.empty:
                smooth = sub["iou"].rolling(window=25, center=True, min_periods=1).mean()
                label = "原始模型" if variant == "baseline" else "改进后跟踪器"
                ax.plot(sub["frame"], smooth, color=COLORS[variant], lw=2.0, label=label)
        ax.set_xlabel("frame index")
        ax.set_ylabel("IoU")
        ax.set_title(f"Smoothed IoU on {sequence}")
        ax.set_ylim(0, 1.02)
        ax.grid(True, linestyle="--", alpha=0.32)
        ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(fig_dir / "iou_curve.png")
        plt.close(fig)
        state.outputs["iou_curve"] = rel(fig_dir / "iou_curve.png", state.out_dir)


def generate_visuals(state: DemoState, paths: dict[str, Path], baseline_pred_dir: Path, atr_pred_dir: Path, atr_input_root: Path) -> None:
    ensure_visual_dependencies()
    videos_dir = state.out_dir / "videos"
    figures_dir = state.out_dir / "figures"
    tables_dir = state.out_dir / "tables"
    videos_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    for sequence in state.sequences:
        row = build_sequence(
            sequence=sequence,
            data_root=paths["data_root"],
            gt_dir=paths["gt_dir"],
            baseline_dir=baseline_pred_dir,
            atr_dir=atr_pred_dir,
            atr_input_root=atr_input_root,
            out_dir=videos_dir,
            fig_dir=figures_dir,
            fps=12.0,
            size=(480, 360),
            sheet_frames=12,
            gif_frames=80,
        )
        input_full = Path(str(row["input_video"]))
        output_full = Path(str(row["output_video"]))
        atr_full = Path(str(row["atr_compare_video"])) if row.get("atr_compare_video") else None
        input_browser = make_browser_mp4(state, input_full)
        output_browser = make_browser_mp4(state, output_full)
        atr_browser = make_browser_mp4(state, atr_full) if atr_full is not None else None
        state.outputs[f"{sequence}:manifest"] = rel(tables_dir / "sequence_visualization_manifest.csv", state.out_dir)
        state.outputs[f"{sequence}:input_full_video"] = rel(input_full, state.out_dir)
        state.outputs[f"{sequence}:output_full_video"] = rel(output_full, state.out_dir)
        state.outputs[f"{sequence}:atr_compare_full_video"] = rel(atr_full, state.out_dir) if atr_full is not None else ""
        state.outputs[f"{sequence}:input_video"] = rel(input_browser, state.out_dir)
        state.outputs[f"{sequence}:output_video"] = rel(output_browser, state.out_dir)
        state.outputs[f"{sequence}:atr_compare_video"] = rel(atr_browser, state.out_dir) if atr_browser is not None else ""
        state.outputs[f"{sequence}:input_preview"] = rel(Path(str(row["input_preview"])), state.out_dir)
        state.outputs[f"{sequence}:output_preview"] = rel(Path(str(row["output_preview"])), state.out_dir)
        state.outputs[f"{sequence}:atr_compare_preview"] = rel(Path(str(row["atr_compare_preview"])), state.out_dir) if row.get("atr_compare_preview") else ""


def copy_manifest_for_visuals(state: DemoState) -> None:
    # build_sequence writes a global manifest only from the call-local table_dir in the standalone CLI.
    # For the demo we write a compact equivalent from the dashboard state.
    rows = []
    for sequence in state.sequences:
        rows.append(
            {
                "sequence": sequence,
                "input_video": state.outputs.get(f"{sequence}:input_video", ""),
                "output_video": state.outputs.get(f"{sequence}:output_video", ""),
                "atr_compare_video": state.outputs.get(f"{sequence}:atr_compare_video", ""),
                "input_preview": state.outputs.get(f"{sequence}:input_preview", ""),
                "output_preview": state.outputs.get(f"{sequence}:output_preview", ""),
                "atr_compare_preview": state.outputs.get(f"{sequence}:atr_compare_preview", ""),
            }
        )
    table = state.out_dir / "tables" / "sequence_visualization_manifest.csv"
    table.parent.mkdir(parents=True, exist_ok=True)
    with table.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "sequence",
                "input_video",
                "output_video",
                "atr_compare_video",
                "input_preview",
                "output_preview",
                "atr_compare_preview",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def run_demo(state: DemoState) -> None:
    state.out_dir.mkdir(parents=True, exist_ok=True)
    set_stage(state, "precheck", "running", "checking CUDA, checkpoint, data, official test entry")
    paths = precheck(state)
    set_stage(state, "precheck", "done", "all required resources are available")
    if not state.no_browser:
        webbrowser.open((state.out_dir / "index.html").resolve().as_uri())

    baseline_pred_dir: Path
    atr_pred_dir: Path
    atr_input_root: Path
    if state.replay_only:
        set_stage(state, "load replay predictions", "running", "copy existing baseline and ATR-GTP predictions")
        baseline_pred_dir, atr_pred_dir, atr_input_root = collect_replay_predictions(state, paths)
        set_stage(state, "load replay predictions", "done", "existing prediction files copied")
    else:
        set_stage(state, "run original SDTrack-Tiny", "running", "calling official tracking/test.py on original GTP input")
        baseline_results_root = state.out_dir / "results" / "baseline"
        for sequence in state.sequences:
            run_tracker_sequence(state, paths, paths["source_root"], baseline_results_root, "baseline", sequence)
        baseline_pred_dir = baseline_results_root / "SDTrack" / "SDTrack-tiny-fe108"
        set_stage(state, "run original SDTrack-Tiny", "done", "baseline prediction files generated")

        set_stage(state, "prepare ATR-GTP input", "running", "generating adaptive_smooth trajectory-channel input")
        ensure_atr_dependencies()
        dataset_root, transform_rows = prepare_variant_dataset(paths["source_root"], state.out_dir / "atr_gtp", "adaptive_smooth", state.sequences)
        if transform_rows:
            transform_log = state.out_dir / "atr_gtp" / "variant_transform_log.csv"
            with transform_log.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=["variant", "sequence", "frame", "event_density", "density_ref", "beta"])
                writer.writeheader()
                writer.writerows(transform_rows)
        atr_input_root = dataset_root
        set_stage(state, "prepare ATR-GTP input", "done", "adaptive_smooth input frames generated")

        set_stage(state, "run improved tracker", "running", "calling official tracking/test.py on ATR-GTP input")
        atr_results_root = state.out_dir / "results" / "adaptive_smooth"
        for sequence in state.sequences:
            run_tracker_sequence(state, paths, atr_input_root, atr_results_root, "adaptive_smooth", sequence)
        atr_pred_dir = atr_results_root / "SDTrack" / "SDTrack-tiny-fe108"
        set_stage(state, "run improved tracker", "done", "ATR-GTP prediction files generated")

    set_stage(state, "evaluate", "running", "computing AUC, PR20, NP@0.2, mean IoU and center error")
    evaluate_demo(state, baseline_pred_dir, atr_pred_dir, paths["gt_dir"])
    set_stage(state, "evaluate", "done", "metrics written to demo output")

    set_stage(state, "visualize", "running", "rendering videos, charts, prediction samples and dashboard")
    generate_visuals(state, paths, baseline_pred_dir, atr_pred_dir, atr_input_root)
    copy_manifest_for_visuals(state)
    plot_demo_figures(state)
    set_stage(state, "visualize", "done", "dashboard assets generated")

    state.status = "complete"
    state.current_stage = "complete"
    render_dashboard(state)
    log_line(state, "demo complete")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a live SDTrack demo with baseline and ATR-GTP inference.")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--sequence", action="append", help="FE108 sequence name. Can be passed multiple times or comma-separated.")
    parser.add_argument("--long-demo", action="store_true")
    parser.add_argument("--replay-only", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--list-sequences", action="store_true")
    parser.add_argument("--out-dir", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo_root).resolve()
    if args.list_sequences:
        demo_root = repo / "demo_assets" / "FE108" / "test"
        project_demo_sequences = sorted(path.name for path in demo_root.iterdir() if (path / "inter1_stack_3008").exists()) if demo_root.exists() else []
        print("Project-contained demo sequences:")
        if project_demo_sequences:
            for name in project_demo_sequences:
                print(f"  {name:14s} {RECOMMENDED_SEQUENCES.get(name, '')}")
        else:
            print("  <none found>")
        print("\nAdditional recommended sequences when full FE108 data is available:")
        for name, note in RECOMMENDED_SEQUENCES.items():
            if name not in project_demo_sequences:
                print(f"  {name:14s} {note}")
        names = available_sequences(repo)
        print("\nAvailable FE108 sequences in this project:")
        print("  " + ", ".join(names) if names else "  <none found>")
        return 0

    sequences = split_sequence_args(args.sequence)
    if args.long_demo and "star_motion" not in sequences:
        sequences.append("star_motion")
    out_dir = Path(args.out_dir).resolve() if args.out_dir else repo / "outputs" / "demo" / datetime.now().strftime("%Y%m%d_%H%M%S")
    state = DemoState(repo=repo, out_dir=out_dir, sequences=sequences, replay_only=args.replay_only, no_browser=args.no_browser)
    try:
        run_demo(state)
        print(f"Demo dashboard: {(state.out_dir / 'index.html').resolve()}")
        return 0
    except Exception as exc:
        state.status = "failed"
        state.current_stage = "failed"
        state.error = str(exc)
        log_line(state, f"FAILED: {exc}")
        render_dashboard(state)
        print(f"Demo failed. Dashboard: {(state.out_dir / 'index.html').resolve()}", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
