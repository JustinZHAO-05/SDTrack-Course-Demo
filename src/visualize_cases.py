from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


COLORS = {
    "gt": (215, 75, 75),
    "baseline": (28, 100, 180),
    "atr": (46, 159, 104),
    "text": (16, 32, 51),
    "muted": (94, 106, 117),
    "paper": (251, 250, 246),
    "panel": (255, 255, 255),
    "line": (203, 213, 225),
    "soft": (241, 246, 250),
}


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def read_boxes(path: Path) -> np.ndarray:
    rows: list[list[float]] = []
    if not path.exists():
        return np.zeros((0, 4), dtype=float)
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip().replace(",", " ").replace("\t", " ")
        if not line:
            continue
        vals = [float(x) for x in line.split()[:4]]
        if len(vals) == 4:
            rows.append(vals)
    return np.asarray(rows, dtype=float)


def iou_xywh(a: np.ndarray, b: np.ndarray) -> float:
    ax1, ay1, aw, ah = [float(x) for x in a]
    bx1, by1, bw, bh = [float(x) for x in b]
    ax2, ay2 = ax1 + max(aw, 0), ay1 + max(ah, 0)
    bx2, by2 = bx1 + max(bw, 0), by1 + max(bh, 0)
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = max(aw, 0) * max(ah, 0) + max(bw, 0) * max(bh, 0) - inter
    return inter / union if union > 0 else 0.0


def frame_path(data_root: Path, sequence: str, frame_index: int) -> Path | None:
    base = data_root / "test" / sequence / "inter1_stack_3008"
    for idx in (frame_index + 1, frame_index):
        for suffix in ("_1.png", ".png", ".jpg"):
            path = base / f"{idx:04d}{suffix}"
            if path.exists():
                return path
    files = sorted(base.glob("*.png"))
    if 0 <= frame_index < len(files):
        return files[frame_index]
    return files[0] if files else None


def scale_box(box: np.ndarray, sx: float, sy: float, ox: int = 0, oy: int = 0) -> tuple[int, int, int, int]:
    x, y, w, h = [float(v) for v in box[:4]]
    return (
        int(round(x * sx + ox)),
        int(round(y * sy + oy)),
        int(round((x + w) * sx + ox)),
        int(round((y + h) * sy + oy)),
    )


def draw_box(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: tuple[int, int, int], width: int = 4) -> None:
    draw.rectangle(box, outline=color, width=width)


def enhance_event_frame(img: Image.Image) -> Image.Image:
    arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    brightness = arr.max(axis=2)
    active = brightness > 3
    if np.count_nonzero(active) > 32:
        hi = float(np.percentile(brightness[active], 99.4))
        hi = max(hi, 16.0)
        arr = np.clip(arr / hi, 0.0, 1.0)
    else:
        arr = np.clip(arr / 255.0, 0.0, 1.0)
    arr = np.power(arr, 0.62)
    arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def make_clean_tile(
    frame: Path,
    gt: np.ndarray | None,
    baseline: np.ndarray | None,
    atr: np.ndarray | None,
    size: tuple[int, int],
) -> Image.Image:
    img = enhance_event_frame(Image.open(frame).convert("RGB"))
    tile = img.resize(size, Image.Resampling.BILINEAR)
    draw = ImageDraw.Draw(tile)
    sx, sy = size[0] / img.width, size[1] / img.height
    if gt is not None:
        draw_box(draw, scale_box(gt, sx, sy), COLORS["gt"], width=5)
    if baseline is not None:
        draw_box(draw, scale_box(baseline, sx, sy), COLORS["baseline"], width=5)
    if atr is not None:
        draw_box(draw, scale_box(atr, sx, sy), COLORS["atr"], width=5)
    return tile


def make_clean_grid(tiles: list[Image.Image], out: Path, columns: int = 3, gap: int = 18) -> None:
    if not tiles:
        return
    tile_w, tile_h = tiles[0].size
    rows = int(np.ceil(len(tiles) / columns))
    canvas = Image.new("RGB", (columns * tile_w + (columns - 1) * gap, rows * tile_h + (rows - 1) * gap), (255, 255, 255))
    for idx, tile in enumerate(tiles):
        row, col = divmod(idx, columns)
        canvas.paste(tile, (col * (tile_w + gap), row * (tile_h + gap)))
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)


def make_panel(
    frame: Path,
    gt: np.ndarray | None,
    baseline: np.ndarray | None,
    atr: np.ndarray | None,
    size: tuple[int, int],
    title: str,
    note: str,
) -> Image.Image:
    panel = Image.new("RGB", size, COLORS["panel"])
    draw = ImageDraw.Draw(panel)
    draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=12, outline=COLORS["line"], width=2, fill=COLORS["panel"])
    draw.text((14, 10), title, fill=COLORS["text"], font=font(20))
    draw.text((14, size[1] - 31), note, fill=COLORS["muted"], font=font(14))

    img = Image.open(frame).convert("RGB")
    area = (14, 44, size[0] - 14, size[1] - 42)
    aw, ah = area[2] - area[0], area[3] - area[1]
    scale = min(aw / img.width, ah / img.height)
    nw, nh = int(img.width * scale), int(img.height * scale)
    shown = img.resize((nw, nh), Image.Resampling.BILINEAR)
    ox = area[0] + (aw - nw) // 2
    oy = area[1] + (ah - nh) // 2
    panel.paste(shown, (ox, oy))
    overlay = ImageDraw.Draw(panel)
    sx, sy = nw / img.width, nh / img.height
    if gt is not None:
        draw_box(overlay, scale_box(gt, sx, sy, ox, oy), COLORS["gt"])
    if baseline is not None:
        draw_box(overlay, scale_box(baseline, sx, sy, ox, oy), COLORS["baseline"])
    if atr is not None:
        draw_box(overlay, scale_box(atr, sx, sy, ox, oy), COLORS["atr"])
    return panel


def draw_legend(draw: ImageDraw.ImageDraw, xy: tuple[int, int]) -> None:
    x, y = xy
    items = [("GT", COLORS["gt"]), ("SDTrack", COLORS["baseline"]), ("ATR-GTP", COLORS["atr"])]
    for idx, (label, color) in enumerate(items):
        xx = x + idx * 150
        draw.rectangle((xx, y, xx + 34, y + 18), outline=color, width=4)
        draw.text((xx + 44, y - 2), label, fill=COLORS["text"], font=font(15))


def load_triplet(
    gt_dir: Path,
    base_dir: Path,
    atr_dir: Path,
    sequence: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    gt = read_boxes(gt_dir / f"{sequence}.txt")
    base = read_boxes(base_dir / f"{sequence}.txt")
    atr = read_boxes(atr_dir / f"{sequence}.txt")
    n = min(len(gt), len(base), len(atr))
    return gt[:n], base[:n], atr[:n]


def draw_dataset_samples(data_root: Path, out: Path) -> None:
    samples = [
        ("star_motion", 680, "快速运动"),
        ("bike_low", 160, "低事件密度"),
        ("dog_motion", 1040, "形变与运动"),
        ("box_hdr", 420, "高动态范围"),
        ("star_mul222", 830, "相似目标"),
        ("airplane_mul222", 460, "多目标干扰"),
    ]
    tiles: list[Image.Image] = []
    for seq, frame_idx, _tag in samples:
        path = frame_path(data_root, seq, frame_idx)
        if path is None:
            continue
        tiles.append(make_clean_tile(path, None, None, None, (430, 323)))
    make_clean_grid(tiles, out)


def draw_tracking_process(data_root: Path, gt_dir: Path, base_dir: Path, atr_dir: Path, out: Path) -> None:
    sequence = "star_motion"
    frames = [120, 440, 760, 1120, 1510, 2010]
    gt, base, atr = load_triplet(gt_dir, base_dir, atr_dir, sequence)
    tiles: list[Image.Image] = []
    for frame_idx in frames:
        if frame_idx >= len(gt):
            continue
        path = frame_path(data_root, sequence, frame_idx)
        if path is None:
            continue
        tiles.append(make_clean_tile(path, gt[frame_idx], base[frame_idx], atr[frame_idx], (430, 323)))
    make_clean_grid(tiles, out)


def select_case_frames(gt: np.ndarray, base: np.ndarray, atr: np.ndarray) -> tuple[int, int]:
    valid = (gt[:, 2] > 2) & (gt[:, 3] > 2) & np.all(np.isfinite(gt), axis=1)
    ious_base = np.asarray([iou_xywh(base[i], gt[i]) if valid[i] else np.nan for i in range(len(gt))])
    ious_atr = np.asarray([iou_xywh(atr[i], gt[i]) if valid[i] else np.nan for i in range(len(gt))])
    mean_iou = np.nanmean(np.vstack([ious_base, ious_atr]), axis=0)
    success_idx = int(np.nanargmax(mean_iou))
    candidate = np.where(valid & (np.arange(len(gt)) > 8))[0]
    if len(candidate):
        failure_idx = int(candidate[np.nanargmin(ious_base[candidate])])
    else:
        failure_idx = int(np.nanargmin(ious_base))
    return success_idx, failure_idx


def draw_real_cases(data_root: Path, gt_dir: Path, base_dir: Path, atr_dir: Path, out: Path) -> None:
    sequences = ["dog_motion", "box_hdr", "bike_low", "star_motion", "star_mul222", "box_hdr"]
    roles = ["成功：形变目标", "成功：高动态范围", "成功：低事件密度", "失败：快速运动低 IoU", "失败：相似目标干扰", "失败：尺度响应偏差"]
    selected: list[tuple[str, int, str]] = []
    cache: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, int, int]] = {}
    for seq in sorted(set(sequences)):
        gt, base, atr = load_triplet(gt_dir, base_dir, atr_dir, seq)
        s_idx, f_idx = select_case_frames(gt, base, atr)
        cache[seq] = (gt, base, atr, s_idx, f_idx)
    for seq, role in zip(sequences, roles):
        gt, base, atr, s_idx, f_idx = cache[seq]
        selected.append((seq, s_idx if role.startswith("成功") else f_idx, role))

    tiles: list[Image.Image] = []
    for seq, frame_idx, _role in selected:
        gt, base, atr, _, _ = cache[seq]
        if frame_idx >= len(gt):
            continue
        path = frame_path(data_root, seq, frame_idx)
        if path is None:
            continue
        tiles.append(make_clean_tile(path, gt[frame_idx], base[frame_idx], atr[frame_idx], (430, 323)))
    make_clean_grid(tiles, out)


def draw_schematic(out: Path) -> None:
    image = Image.new("RGB", (1300, 860), COLORS["paper"])
    draw = ImageDraw.Draw(image)
    draw.text((42, 30), "成功与失败模式示意图", fill=COLORS["text"], font=font(34))
    draw.text((42, 82), "该图是机制归因示意图；真实帧截图见后续数据集样例、推理过程和案例可视化。", fill=COLORS["muted"], font=font(18))
    labels = [
        ("成功", "GTP", COLORS["atr"]),
        ("中心漂移", "IPL", COLORS["baseline"]),
        ("尺度失配", "SSA", COLORS["gt"]),
        ("背景吸附", "Head", COLORS["baseline"]),
        ("快速运动", "beta", COLORS["atr"]),
        ("低事件密度", "GTP", COLORS["muted"]),
    ]
    for idx, (title, tag, color) in enumerate(labels):
        row, col = divmod(idx, 3)
        x, y = 45 + col * 405, 135 + row * 325
        draw.rounded_rectangle((x, y, x + 370, y + 285), radius=12, fill=COLORS["panel"], outline=COLORS["line"], width=2)
        draw.text((x + 18, y + 15), title, fill=color, font=font(22))
        draw.rounded_rectangle((x + 285, y + 15, x + 345, y + 42), radius=5, fill=COLORS["soft"], outline=color, width=2)
        draw.text((x + 300, y + 18), tag, fill=COLORS["text"], font=font(13))
        scene = (x + 18, y + 58, x + 352, y + 210)
        draw.rectangle(scene, fill=(242, 246, 250), outline=COLORS["line"])
        sx, sy, ex, ey = scene
        for k in range(22):
            xx = sx + 12 + k * 14
            draw.point((xx, sy + 35 + (k * 19) % 92), fill=(60, 120, 200))
            draw.point((xx + 6, sy + 25 + (k * 31) % 102), fill=(210, 70, 80))
        gt = (sx + 145, sy + 48, sx + 218, sy + 106)
        base = (sx + 130 + (idx % 3) * 18, sy + 54, sx + 205 + (idx % 3) * 22, sy + 116)
        atr = (sx + 148, sy + 50, sx + 220, sy + 109)
        draw.rectangle(gt, outline=COLORS["gt"], width=3)
        draw.rectangle(base, outline=COLORS["baseline"], width=3)
        draw.rectangle(atr, outline=COLORS["atr"], width=3)
        draw.line((x + 30, y + 238, x + 342, y + 238), fill=COLORS["line"], width=2)
        draw.text((x + 22, y + 248), "示意：红 GT / 蓝 SDTrack / 绿 ATR-GTP", fill=COLORS["muted"], font=font(13))
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)


def draw_real_case_grid(cases: list[dict], data_root: Path, out: Path, max_cases: int = 6) -> bool:
    selected = []
    used = set()
    for case in cases:
        seq = str(case.get("sequence", ""))
        if seq in used:
            continue
        path = frame_path(data_root, seq, int(case.get("frame_index", 0)))
        gt = np.asarray(case.get("gt_xywh", []), dtype=float)
        pred = np.asarray(case.get("pred_xywh", []), dtype=float)
        if path is not None and len(gt) == 4 and len(pred) == 4 and gt[2] > 2 and gt[3] > 2:
            selected.append((case, path, gt, pred))
            used.add(seq)
        if len(selected) >= max_cases:
            break
    if not selected:
        return False
    tiles = [make_clean_tile(path, gt, pred, None, (430, 323)) for _case, path, gt, pred in selected]
    make_clean_grid(tiles, out)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Create real tracking visualizations for SDTrack.")
    parser.add_argument("--cases", default="outputs/metrics/failure_cases.json")
    parser.add_argument("--out", default="outputs/cases")
    parser.add_argument("--data-root", default="data/FE108")
    parser.add_argument("--gt-dir", default="data/official_results_E/FE108_eval/FE108/annos/gt_rect")
    parser.add_argument("--baseline-dir", default="outputs/test/tracking_results/SDTrack/SDTrack-tiny-fe108")
    parser.add_argument("--atr-dir", default="outputs/atr_gtp_tracking/results/adaptive_smooth/SDTrack/SDTrack-tiny-fe108")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    data_root = Path(args.data_root)
    gt_dir = Path(args.gt_dir)
    base_dir = Path(args.baseline_dir)
    atr_dir = Path(args.atr_dir)

    draw_schematic(out / "caseboard_schematic.png")
    draw_dataset_samples(data_root, out / "dataset_event_samples.png")
    draw_tracking_process(data_root, gt_dir, base_dir, atr_dir, out / "tracking_process_star_motion.png")
    draw_real_cases(data_root, gt_dir, base_dir, atr_dir, out / "real_tracking_cases.png")

    case_path = Path(args.cases)
    if case_path.exists():
        cases = json.loads(case_path.read_text(encoding="utf-8"))
        (out / "failure_cases_used.json").write_text(json.dumps(cases[:20], ensure_ascii=False, indent=2), encoding="utf-8")
        draw_real_case_grid(cases, data_root, out / "failure_case_grid.png")
    print(f"Wrote case visualization to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
