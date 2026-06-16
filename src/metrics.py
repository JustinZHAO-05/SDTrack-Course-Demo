from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class SequenceMetrics:
    sequence: str
    frames: int
    auc: float
    pr20: float
    norm_precision_020: float
    mean_iou: float
    mean_center_error: float
    failure_rate_iou_010: float


def load_xywh(path: str | Path) -> np.ndarray:
    """Load an xywh text file with comma, tab, or whitespace delimiters."""
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return np.empty((0, 4), dtype=np.float64)
    rows: list[list[float]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = line.replace(",", " ").replace("\t", " ")
        values = [float(part) for part in line.split()[:4]]
        if len(values) == 4:
            rows.append(values)
    return np.asarray(rows, dtype=np.float64)


def load_vector(path: str | Path) -> np.ndarray:
    """Load a one-column numeric annotation file such as absent flags."""
    path = Path(path)
    if not path.exists():
        return np.empty((0,), dtype=np.float64)
    rows: list[float] = []
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip().replace(",", " ").replace("\t", " ")
        if not line:
            continue
        try:
            rows.append(float(line.split()[0]))
        except ValueError:
            continue
    return np.asarray(rows, dtype=np.float64)


def align_boxes(pred: np.ndarray, gt: np.ndarray, valid: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    n = min(len(pred), len(gt))
    if n <= 0:
        return pred[:0], gt[:0]
    pred_out = pred[:n, :4].astype(np.float64)
    gt_out = gt[:n, :4].astype(np.float64)
    if valid is not None and len(valid):
        mask = np.asarray(valid[:n]).astype(bool)
        pred_out = pred_out[mask]
        gt_out = gt_out[mask]
    return pred_out, gt_out


def xywh_to_xyxy(boxes: np.ndarray) -> np.ndarray:
    out = boxes.copy().astype(np.float64)
    out[:, 2] = out[:, 0] + np.maximum(out[:, 2], 0)
    out[:, 3] = out[:, 1] + np.maximum(out[:, 3], 0)
    return out


def iou_xywh(pred: np.ndarray, gt: np.ndarray) -> np.ndarray:
    pred_xyxy = xywh_to_xyxy(pred)
    gt_xyxy = xywh_to_xyxy(gt)
    left_top = np.maximum(pred_xyxy[:, :2], gt_xyxy[:, :2])
    right_bottom = np.minimum(pred_xyxy[:, 2:], gt_xyxy[:, 2:])
    wh = np.maximum(right_bottom - left_top, 0)
    inter = wh[:, 0] * wh[:, 1]
    pred_area = np.maximum(pred[:, 2], 0) * np.maximum(pred[:, 3], 0)
    gt_area = np.maximum(gt[:, 2], 0) * np.maximum(gt[:, 3], 0)
    union = pred_area + gt_area - inter
    return np.divide(inter, union, out=np.zeros_like(inter), where=union > 0)


def center_error_xywh(pred: np.ndarray, gt: np.ndarray) -> np.ndarray:
    pred_c = pred[:, :2] + pred[:, 2:4] / 2.0
    gt_c = gt[:, :2] + gt[:, 2:4] / 2.0
    return np.linalg.norm(pred_c - gt_c, axis=1)


def normalized_center_error_xywh(pred: np.ndarray, gt: np.ndarray) -> np.ndarray:
    errors = center_error_xywh(pred, gt)
    scale = np.sqrt(np.maximum(gt[:, 2], 1e-6) * np.maximum(gt[:, 3], 1e-6))
    return np.divide(errors, scale, out=np.zeros_like(errors), where=scale > 0)


def success_curve(ious: np.ndarray, thresholds: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray, float]:
    if thresholds is None:
        thresholds = np.linspace(0.0, 1.0, 101)
    values = np.asarray([(ious >= thr).mean() if len(ious) else 0.0 for thr in thresholds])
    auc = float(values.mean())
    return thresholds, values, auc


def precision_curve(errors: np.ndarray, thresholds: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray, float]:
    if thresholds is None:
        thresholds = np.arange(0, 51, 1)
    values = np.asarray([(errors <= thr).mean() if len(errors) else 0.0 for thr in thresholds])
    pr20 = float(values[np.where(thresholds == 20)[0][0]]) if 20 in thresholds else float((errors <= 20).mean())
    return thresholds, values, pr20


def normalized_precision_curve(errors: np.ndarray, thresholds: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray, float]:
    if thresholds is None:
        thresholds = np.linspace(0.0, 0.5, 101)
    values = np.asarray([(errors <= thr).mean() if len(errors) else 0.0 for thr in thresholds])
    if np.any(np.isclose(thresholds, 0.2)):
        idx = int(np.where(np.isclose(thresholds, 0.2))[0][0])
        score = float(values[idx])
    else:
        score = float((errors <= 0.2).mean()) if len(errors) else 0.0
    return thresholds, values, score


def compute_sequence_metrics(sequence: str, pred: np.ndarray, gt: np.ndarray, valid: np.ndarray | None = None) -> tuple[SequenceMetrics, dict[str, np.ndarray]]:
    pred, gt = align_boxes(pred, gt, valid)
    ious = iou_xywh(pred, gt)
    errors = center_error_xywh(pred, gt)
    norm_errors = normalized_center_error_xywh(pred, gt)
    _, _, auc = success_curve(ious)
    _, _, pr20 = precision_curve(errors)
    _, _, norm_precision_020 = normalized_precision_curve(norm_errors)
    metrics = SequenceMetrics(
        sequence=sequence,
        frames=int(len(pred)),
        auc=auc,
        pr20=pr20,
        norm_precision_020=norm_precision_020,
        mean_iou=float(ious.mean()) if len(ious) else 0.0,
        mean_center_error=float(errors.mean()) if len(errors) else 0.0,
        failure_rate_iou_010=float((ious < 0.10).mean()) if len(ious) else 0.0,
    )
    return metrics, {"pred": pred, "gt": gt, "iou": ious, "center_error": errors, "norm_center_error": norm_errors}


def discover_txt_files(path: str | Path) -> list[Path]:
    path = Path(path)
    if path.is_file():
        return [path]
    ignored_suffixes = ("_time", "_all_boxes", "_all_scores")
    files = []
    for item in sorted(path.rglob("*.txt")):
        stem = item.stem.lower()
        if any(stem.endswith(suffix) for suffix in ignored_suffixes):
            continue
        files.append(item)
    return files


def sequence_name_from_path(path: Path) -> str:
    name = path.stem
    for suffix in ("_gt", "_groundtruth", "_pred"):
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    if name.lower().startswith("groundtruth"):
        return path.parent.name
    return name


def pair_prediction_and_gt(pred_path: str | Path, gt_path: str | Path) -> list[tuple[str, Path, Path]]:
    pred_files = discover_txt_files(pred_path)
    gt_files = discover_txt_files(gt_path)
    pred_by_name = {sequence_name_from_path(p): p for p in pred_files}
    gt_by_name = {sequence_name_from_path(g): g for g in gt_files}
    pairs = []
    for name, pred_file in sorted(pred_by_name.items()):
        gt_file = gt_by_name.get(name)
        if gt_file is None:
            gt_file = gt_by_name.get(Path(pred_file).parent.name)
        if gt_file is not None:
            pairs.append((name, pred_file, gt_file))
    if not pairs and len(pred_files) == 1 and len(gt_files) == 1:
        pairs.append((sequence_name_from_path(pred_files[0]), pred_files[0], gt_files[0]))
    return pairs


def weighted_average(values: Iterable[tuple[float, int]]) -> float:
    total = 0.0
    count = 0
    for value, weight in values:
        total += float(value) * int(weight)
        count += int(weight)
    return total / count if count else 0.0
