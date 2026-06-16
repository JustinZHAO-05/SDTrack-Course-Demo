from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np
from PIL import Image, ImageDraw


COLORS = {
    "gt": (215, 75, 75),
    "baseline": (28, 100, 180),
    "atr": (46, 159, 104),
}


def read_boxes(path: Path) -> np.ndarray:
    rows: list[list[float]] = []
    if not path.exists():
        return np.empty((0, 4), dtype=np.float64)
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip().replace(",", " ").replace("\t", " ")
        if not line:
            continue
        values = [float(x) for x in line.split()[:4]]
        if len(values) == 4:
            rows.append(values)
    return np.asarray(rows, dtype=np.float64)


def escape_tex(text: str) -> str:
    return text.replace("\\", "\\textbackslash{}").replace("_", "\\_")


def frame_files(data_root: Path, sequence: str) -> list[Path]:
    frame_dir = data_root / "test" / sequence / "inter1_stack_3008"
    return sorted(frame_dir.glob("*.png"))


def variant_frame_files(variant_root: Path, sequence: str) -> list[Path]:
    frame_dir = variant_root / sequence / "inter1_stack_3008"
    return sorted(frame_dir.glob("*.png"))


def load_gt(data_root: Path, gt_dir: Path | None, sequence: str) -> np.ndarray:
    candidates = [data_root / "test" / sequence / "groundtruth_rect.txt"]
    if gt_dir is not None:
        candidates.append(gt_dir / f"{sequence}.txt")
    for path in candidates:
        boxes = read_boxes(path)
        if len(boxes):
            return boxes
    return np.empty((0, 4), dtype=np.float64)


def enhance_event_frame(image: Image.Image) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    brightness = arr.max(axis=2)
    active = brightness > 3
    if np.count_nonzero(active) > 32:
        hi = float(np.percentile(brightness[active], 99.3))
        lo = float(np.percentile(brightness[active], 5.0))
        hi = max(hi, lo + 8.0, 18.0)
        arr = np.clip((arr - lo) / (hi - lo), 0.0, 1.0)
    else:
        arr = np.clip(arr / 255.0, 0.0, 1.0)
    arr = np.power(arr, 0.58)
    return Image.fromarray(np.clip(arr * 255.0, 0, 255).astype(np.uint8), mode="RGB")


def scale_box(box: np.ndarray, sx: float, sy: float) -> tuple[int, int, int, int]:
    x, y, w, h = [float(v) for v in box[:4]]
    return (
        int(round(x * sx)),
        int(round(y * sy)),
        int(round((x + max(w, 0.0)) * sx)),
        int(round((y + max(h, 0.0)) * sy)),
    )


def draw_box(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: tuple[int, int, int], width: int) -> None:
    draw.rectangle(box, outline=color, width=width)


def render_frame(
    path: Path,
    size: tuple[int, int],
    gt: np.ndarray | None = None,
    baseline: np.ndarray | None = None,
    atr: np.ndarray | None = None,
) -> Image.Image:
    src = enhance_event_frame(Image.open(path).convert("RGB"))
    shown = src.resize(size, Image.Resampling.BILINEAR)
    draw = ImageDraw.Draw(shown)
    sx, sy = size[0] / src.width, size[1] / src.height
    width = max(3, round(size[0] / 180))
    if gt is not None:
        draw_box(draw, scale_box(gt, sx, sy), COLORS["gt"], width)
    if baseline is not None:
        draw_box(draw, scale_box(baseline, sx, sy), COLORS["baseline"], width)
    if atr is not None:
        draw_box(draw, scale_box(atr, sx, sy), COLORS["atr"], width)
    return shown


def render_base_frame(path: Path, size: tuple[int, int]) -> tuple[Image.Image, tuple[int, int]]:
    src = enhance_event_frame(Image.open(path).convert("RGB"))
    return src.resize(size, Image.Resampling.BILINEAR), (src.width, src.height)


def draw_boxes_on_frame(
    image: Image.Image,
    source_size: tuple[int, int],
    gt: np.ndarray | None = None,
    baseline: np.ndarray | None = None,
    atr: np.ndarray | None = None,
) -> Image.Image:
    shown = image.copy()
    draw = ImageDraw.Draw(shown)
    sx, sy = shown.width / source_size[0], shown.height / source_size[1]
    width = max(3, round(shown.width / 180))
    if gt is not None:
        draw_box(draw, scale_box(gt, sx, sy), COLORS["gt"], width)
    if baseline is not None:
        draw_box(draw, scale_box(baseline, sx, sy), COLORS["baseline"], width)
    if atr is not None:
        draw_box(draw, scale_box(atr, sx, sy), COLORS["atr"], width)
    return shown


class Mp4Sink:
    def __init__(self, out: Path, fps: float) -> None:
        self.out = out
        self.fps = fps
        self.writer: cv2.VideoWriter | None = None
        self.frames = 0
        out.parent.mkdir(parents=True, exist_ok=True)

    def write(self, image: Image.Image) -> None:
        arr = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
        if self.writer is None:
            h, w = arr.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self.writer = cv2.VideoWriter(str(self.out), fourcc, self.fps, (w, h))
            if not self.writer.isOpened():
                raise RuntimeError(f"failed to open video writer: {self.out}")
        self.writer.write(arr)
        self.frames += 1

    def close(self) -> None:
        if self.writer is not None:
            self.writer.release()
            self.writer = None


def file_ready(path: Path) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    if path.suffix.lower() == ".mp4":
        cap = cv2.VideoCapture(str(path))
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        return frames > 0
    return True


def make_grid(images: list[Image.Image], columns: int, gap: int = 8) -> Image.Image:
    if not images:
        raise ValueError("no images for grid")
    tile_w, tile_h = images[0].size
    rows = math.ceil(len(images) / columns)
    canvas = Image.new("RGB", (columns * tile_w + (columns - 1) * gap, rows * tile_h + (rows - 1) * gap), (255, 255, 255))
    for idx, image in enumerate(images):
        row, col = divmod(idx, columns)
        canvas.paste(image, (col * (tile_w + gap), row * (tile_h + gap)))
    return canvas


def sample_indices(n: int, count: int) -> list[int]:
    if n <= 0:
        return []
    if n <= count:
        return list(range(n))
    return sorted({int(round(x)) for x in np.linspace(0, n - 1, count)})


def frame_activity(path: Path) -> float:
    arr = np.asarray(Image.open(path).convert("RGB"))
    return float((arr.max(axis=2) > 3).mean())


def sample_visible_indices(paths: list[Path], count: int, min_activity: float = 0.05) -> list[int]:
    n = len(paths)
    if n <= 0:
        return []
    if n <= count:
        return list(range(n))
    start = min(max(8, int(round(n * 0.04))), n - 1)
    candidates = [idx for idx in range(start, n) if frame_activity(paths[idx]) >= min_activity]
    if len(candidates) < count:
        candidates = list(range(start, n))
    positions = np.linspace(0, len(candidates) - 1, count)
    return [candidates[int(round(pos))] for pos in positions]


def write_mp4(frames: Iterable[Image.Image], out: Path, fps: float) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    writer: cv2.VideoWriter | None = None
    written = 0
    try:
        for image in frames:
            arr = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
            if writer is None:
                h, w = arr.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(str(out), fourcc, fps, (w, h))
                if not writer.isOpened():
                    raise RuntimeError(f"failed to open video writer: {out}")
            writer.write(arr)
            written += 1
    finally:
        if writer is not None:
            writer.release()
    return written


def write_preview_gif(images: list[Image.Image], out: Path, duration_ms: int = 90) -> None:
    if not images:
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    first, rest = images[0], images[1:]
    first.save(out, save_all=True, append_images=rest, duration=duration_ms, loop=0, optimize=True)


def paired_frame(left: Path, right: Path, size: tuple[int, int]) -> Image.Image:
    left_img = render_frame(left, size)
    right_img = render_frame(right, size)
    gap = 8
    canvas = Image.new("RGB", (size[0] * 2 + gap, size[1]), (255, 255, 255))
    canvas.paste(left_img, (0, 0))
    canvas.paste(right_img, (size[0] + gap, 0))
    return canvas


def paired_images(left_img: Image.Image, right_img: Image.Image) -> Image.Image:
    gap = 8
    canvas = Image.new("RGB", (left_img.width + right_img.width + gap, left_img.height), (255, 255, 255))
    canvas.paste(left_img, (0, 0))
    canvas.paste(right_img, (left_img.width + gap, 0))
    return canvas


def build_sequence(
    sequence: str,
    data_root: Path,
    gt_dir: Path | None,
    baseline_dir: Path,
    atr_dir: Path,
    atr_input_root: Path,
    out_dir: Path,
    fig_dir: Path,
    fps: float,
    size: tuple[int, int],
    sheet_frames: int,
    gif_frames: int,
) -> dict[str, str | int]:
    raw_frames = frame_files(data_root, sequence)
    atr_frames = variant_frame_files(atr_input_root, sequence)
    gt = load_gt(data_root, gt_dir, sequence)
    baseline = read_boxes(baseline_dir / f"{sequence}.txt")
    atr = read_boxes(atr_dir / f"{sequence}.txt")
    n = min(len(raw_frames), len(gt), len(baseline), len(atr))
    if n <= 0:
        raise RuntimeError(f"no aligned frames/boxes for {sequence}")

    input_video = out_dir / f"{sequence}_input_full.mp4"
    output_video = out_dir / f"{sequence}_output_overlay_full.mp4"
    atr_compare_video = out_dir / f"{sequence}_atr_input_compare_full.mp4"
    input_gif = out_dir / f"{sequence}_input_preview.gif"
    output_gif = out_dir / f"{sequence}_output_overlay_preview.gif"
    atr_compare_gif = out_dir / f"{sequence}_atr_input_compare_preview.gif"

    atr_compare_frames = min(n, len(atr_frames))
    need_input_video = not file_ready(input_video)
    need_output_video = not file_ready(output_video)
    need_atr_video = atr_compare_frames > 0 and not file_ready(atr_compare_video)
    if need_input_video or need_output_video or need_atr_video:
        input_sink = Mp4Sink(input_video, fps) if need_input_video else None
        output_sink = Mp4Sink(output_video, fps) if need_output_video else None
        atr_sink = Mp4Sink(atr_compare_video, fps) if need_atr_video else None
        try:
            for i in range(n):
                raw_img, source_size = render_base_frame(raw_frames[i], size)
                if input_sink is not None:
                    input_sink.write(raw_img)
                if output_sink is not None:
                    output_sink.write(draw_boxes_on_frame(raw_img, source_size, gt[i], baseline[i], atr[i]))
                if atr_sink is not None and i < atr_compare_frames:
                    atr_img, _ = render_base_frame(atr_frames[i], size)
                    atr_sink.write(paired_images(raw_img, atr_img))
        finally:
            for sink in (input_sink, output_sink, atr_sink):
                if sink is not None:
                    sink.close()

    sheet_idx = sample_visible_indices(raw_frames[:n], sheet_frames)
    gif_idx = sample_visible_indices(raw_frames[:n], gif_frames)
    input_tiles = [render_frame(raw_frames[i], size) for i in sheet_idx]
    output_tiles = [render_frame(raw_frames[i], size, gt[i], baseline[i], atr[i]) for i in sheet_idx]
    input_sheet = fig_dir / f"sequence_{sequence}_input_contact.png"
    output_sheet = fig_dir / f"sequence_{sequence}_output_contact.png"
    make_grid(input_tiles, columns=4).save(input_sheet)
    make_grid(output_tiles, columns=4).save(output_sheet)

    input_preview = [render_frame(raw_frames[i], size) for i in gif_idx]
    output_preview = [render_frame(raw_frames[i], size, gt[i], baseline[i], atr[i]) for i in gif_idx]
    write_preview_gif(input_preview, input_gif)
    write_preview_gif(output_preview, output_gif)

    atr_input_sheet = ""
    if atr_compare_frames > 0:
        compare_idx = sample_visible_indices(raw_frames[:atr_compare_frames], min(sheet_frames // 2, 6))
        top = [render_frame(raw_frames[i], size) for i in compare_idx]
        bottom = [render_frame(atr_frames[i], size) for i in compare_idx]
        atr_input_sheet_path = fig_dir / f"sequence_{sequence}_atr_input_compare.png"
        make_grid(top + bottom, columns=len(compare_idx)).save(atr_input_sheet_path)
        atr_preview = [paired_frame(raw_frames[i], atr_frames[i], size) for i in sample_indices(atr_compare_frames, min(gif_frames, 60))]
        write_preview_gif(atr_preview, atr_compare_gif)
        atr_input_sheet = str(atr_input_sheet_path)

    return {
        "sequence": sequence,
        "frames": n,
        "input_video": str(input_video),
        "output_video": str(output_video),
        "atr_compare_video": str(atr_compare_video) if atr_compare_frames else "",
        "input_preview": str(input_gif),
        "output_preview": str(output_gif),
        "atr_compare_preview": str(atr_compare_gif) if atr_compare_frames else "",
        "input_sheet": str(input_sheet),
        "output_sheet": str(output_sheet),
        "atr_input_sheet": atr_input_sheet,
    }


def write_manifest(rows: list[dict[str, str | int]], out_csv: Path, out_tex: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "\\begin{tabular}{lrlcc}",
        "\\toprule",
        "序列 & 帧数 & 完整输入帧流 & 完整输出帧流 & ATR-GTP输入对比\\\\",
        "\\midrule",
    ]
    for row in rows:
        seq = escape_tex(str(row["sequence"]))
        input_name = escape_tex(Path(str(row["input_video"])).name)
        output_name = escape_tex(Path(str(row["output_video"])).name)
        atr_name = escape_tex(Path(str(row["atr_compare_video"])).name) if row["atr_compare_video"] else "-"
        lines.append(
            f"{seq} & {int(row['frames'])} & \\code{{{input_name}}} & \\code{{{output_name}}} & \\code{{{atr_name}}}\\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}", ""]
    out_tex.parent.mkdir(parents=True, exist_ok=True)
    out_tex.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render complete SDTrack input/output frame streams.")
    parser.add_argument("--data-root", default="data/FE108")
    parser.add_argument("--gt-dir", default="data/official_results_E/FE108_eval/FE108/annos/gt_rect")
    parser.add_argument("--baseline-dir", default="outputs/test/tracking_results/SDTrack/SDTrack-tiny-fe108")
    parser.add_argument("--atr-dir", default="outputs/atr_gtp_tracking/results/adaptive_smooth/SDTrack/SDTrack-tiny-fe108")
    parser.add_argument("--atr-input-root", default="outputs/atr_gtp_tracking/datasets/adaptive_smooth")
    parser.add_argument("--out-dir", default="outputs/sequence_viz")
    parser.add_argument("--fig-dir", default="outputs/cases")
    parser.add_argument("--table-dir", default="outputs/tables")
    parser.add_argument("--sequences", nargs="+", default=["star_motion", "bike_low"])
    parser.add_argument("--fps", type=float, default=12.0)
    parser.add_argument("--width", type=int, default=480)
    parser.add_argument("--height", type=int, default=360)
    parser.add_argument("--sheet-frames", type=int, default=12)
    parser.add_argument("--gif-frames", type=int, default=80)
    args = parser.parse_args()

    data_root = Path(args.data_root)
    gt_dir = Path(args.gt_dir) if args.gt_dir else None
    baseline_dir = Path(args.baseline_dir)
    atr_dir = Path(args.atr_dir)
    atr_input_root = Path(args.atr_input_root)
    out_dir = Path(args.out_dir)
    fig_dir = Path(args.fig_dir)
    table_dir = Path(args.table_dir)

    rows = [
        build_sequence(
            sequence=sequence,
            data_root=data_root,
            gt_dir=gt_dir,
            baseline_dir=baseline_dir,
            atr_dir=atr_dir,
            atr_input_root=atr_input_root,
            out_dir=out_dir,
            fig_dir=fig_dir,
            fps=args.fps,
            size=(args.width, args.height),
            sheet_frames=args.sheet_frames,
            gif_frames=args.gif_frames,
        )
        for sequence in args.sequences
    ]
    write_manifest(
        rows,
        table_dir / "sequence_visualization_manifest.csv",
        table_dir / "sequence_visualization_manifest.tex",
    )
    for row in rows:
        print(f"{row['sequence']}: {row['frames']} frames -> {row['output_video']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
