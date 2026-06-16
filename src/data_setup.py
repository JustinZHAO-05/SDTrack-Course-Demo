from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import time
import zipfile
from pathlib import Path


DEFAULT_SOURCE = Path(os.environ.get("SDTRACK_SOURCE_ROOT", "external_data/raw"))
DEFAULT_WORK = Path(os.environ.get("SDTRACK_WORK_ROOT", "external_data/work"))

RAW_FILES = {
    "FE108.zip": {"kind": "dataset", "target": "FE108"},
    "VisEvent.zip": {"kind": "dataset", "target": "VisEvent"},
    "FE108.tar": {"kind": "eval", "target": "FE108_eval"},
    "VisEvent.tar": {"kind": "eval", "target": "VisEvent_eval"},
    "FE108_tracking_results.zip": {"kind": "results", "target": "FE108_results"},
    "VISEVENT_tracking_results.zip": {"kind": "results", "target": "VisEvent_results"},
    "SDTrack-tiny-1x4.pth": {"kind": "weight", "target": "SDTrack-tiny-1x4.pth"},
    "SDTrack_ep0100.pth.tar": {"kind": "weight", "target": "SDTrack_ep0100.pth.tar"},
    "SDTrack_ep0100.pth (1).tar": {"kind": "weight", "target": "SDTrack_ep0100_visevent.pth.tar"},
}


def sha256_prefix(path: Path, mb: int = 64) -> str:
    h = hashlib.sha256()
    limit = mb * 1024 * 1024
    read = 0
    with path.open("rb") as fh:
        while read < limit:
            chunk = fh.read(min(1024 * 1024, limit - read))
            if not chunk:
                break
            h.update(chunk)
            read += len(chunk)
    return h.hexdigest()


def zip_stats(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as zf:
        infos = zf.infolist()
        return {
            "entries": len(infos),
            "compressed_bytes": sum(info.compress_size for info in infos),
            "uncompressed_bytes": sum(info.file_size for info in infos),
            "first_entry": infos[0].filename if infos else "",
            "last_entry": infos[-1].filename if infos else "",
        }


def ensure_dirs(work_root: Path) -> dict[str, Path]:
    dirs = {
        "raw": work_root / "raw",
        "extracted": work_root / "extracted",
        "weights": work_root / "weights",
        "official_results": work_root / "official_results",
        "logs": work_root / "logs",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def copy_if_needed(src: Path, dst: Path) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size == src.stat().st_size:
        return "exists"
    shutil.copy2(src, dst)
    return "copied"


def extract_zip(src: Path, dst: Path, skip_if_nonempty: bool = True) -> str:
    if skip_if_nonempty and dst.exists() and any(dst.iterdir()):
        return "exists"
    dst.mkdir(parents=True, exist_ok=True)
    seven_zip = shutil.which("7z")
    if seven_zip:
        proc = subprocess.run([seven_zip, "x", "-y", f"-o{dst}", str(src)], capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            return "extracted_7z"
    with zipfile.ZipFile(src) as zf:
        zf.extractall(dst)
    return "extracted"


def extract_tar(src: Path, dst: Path, skip_if_nonempty: bool = True) -> str:
    if skip_if_nonempty and dst.exists() and any(dst.iterdir()):
        return "exists"
    dst.mkdir(parents=True, exist_ok=True)
    with tarfile.open(src) as tf:
        tf.extractall(dst)
    return "extracted"


def is_link_or_junction(path: Path) -> bool:
    return path.exists() and (path.is_symlink() or bool(os.path.islink(path)))


def make_junction(link: Path, target: Path) -> str:
    target = target.resolve()
    if link.exists():
        try:
            if link.resolve() == target:
                return "exists"
        except OSError:
            pass
        return "skipped_existing_path"
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(target, link, target_is_directory=target.is_dir())
        return "symlinked"
    except OSError:
        if target.is_dir():
            proc = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, text=True, check=False)
        else:
            proc = subprocess.run(["cmd", "/c", "mklink", str(link), str(target)], capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            return f"failed: {proc.stderr.strip() or proc.stdout.strip()}"
        return "junction"


def dataset_target(work_root: Path, name: str) -> Path:
    if name == "FE108":
        nested = work_root / "extracted" / "FE108" / "data1" / "dataset" / "full_event_dataset" / "FE108"
        return nested if nested.exists() else work_root / "extracted" / "FE108"
    if name == "VisEvent":
        nested = work_root / "extracted" / "VisEvent" / "VisEvent"
        return nested if nested.exists() else work_root / "extracted" / "VisEvent"
    raise ValueError(name)


def write_official_checkpoints(work_root: Path, repo_root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    mappings = [
        ("SDTrack_ep0100.pth.tar", repo_root / "outputs" / "checkpoints" / "train" / "SDTrack" / "SDTrack-tiny-fe108" / "SDTrack_ep0100.pth.tar"),
        ("SDTrack_ep0100_visevent.pth.tar", repo_root / "outputs" / "checkpoints" / "train" / "SDTrack" / "SDTrack-tiny-visevent" / "SDTrack_ep0100.pth.tar"),
    ]
    for source_name, dst in mappings:
        src = work_root / "weights" / source_name
        if src.exists():
            rows.append({"checkpoint": str(dst), "status": copy_if_needed(src, dst)})
        else:
            rows.append({"checkpoint": str(dst), "status": "missing_source"})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare SDTrack data under an E-drive staging root and link it into the repo.")
    parser.add_argument("--source-root", default=str(DEFAULT_SOURCE))
    parser.add_argument("--work-root", default=str(DEFAULT_WORK))
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--extract-datasets", choices=["none", "fe108", "visevent", "all"], default="none")
    parser.add_argument("--skip-official-extract", action="store_true")
    parser.add_argument("--hash-prefix-mb", type=int, default=64)
    args = parser.parse_args()

    source_root = Path(args.source_root)
    work_root = Path(args.work_root)
    repo_root = Path(args.repo_root).resolve()
    dirs = ensure_dirs(work_root)
    started = time.time()

    status: dict[str, object] = {
        "source_root": str(source_root),
        "work_root": str(work_root),
        "repo_root": str(repo_root),
        "extract_datasets": args.extract_datasets,
        "files": {},
        "actions": [],
    }

    for name, spec in RAW_FILES.items():
        src = source_root / name
        row: dict[str, object] = {"exists": src.exists(), "kind": spec["kind"], "target": spec["target"]}
        if src.exists():
            row["bytes"] = src.stat().st_size
            row["sha256_first_mb"] = sha256_prefix(src, args.hash_prefix_mb)
            if src.suffix.lower() == ".zip":
                row.update(zip_stats(src))
        status["files"][name] = row

    for name, spec in RAW_FILES.items():
        src = source_root / name
        if not src.exists():
            continue
        if spec["kind"] == "weight":
            dst = dirs["weights"] / str(spec["target"])
            status["actions"].append({"action": "copy_weight", "file": name, "status": copy_if_needed(src, dst)})
        elif spec["kind"] in {"eval", "results"} and not args.skip_official_extract:
            dst = dirs["official_results"] / str(spec["target"])
            if src.suffix.lower() == ".zip":
                result = extract_zip(src, dst)
            else:
                result = extract_tar(src, dst)
            status["actions"].append({"action": "extract_official", "file": name, "target": str(dst), "status": result})

    wanted = set()
    if args.extract_datasets in {"fe108", "all"}:
        wanted.add("FE108.zip")
    if args.extract_datasets in {"visevent", "all"}:
        wanted.add("VisEvent.zip")
    for name in sorted(wanted):
        src = source_root / name
        if not src.exists():
            status["actions"].append({"action": "extract_dataset", "file": name, "status": "missing"})
            continue
        dst = dirs["extracted"] / RAW_FILES[name]["target"]
        status["actions"].append({"action": "extract_dataset", "file": name, "target": str(dst), "status": extract_zip(src, dst)})

    links = [
        (repo_root / "data" / "FE108", dataset_target(work_root, "FE108")),
        (repo_root / "data" / "VisEvent", dataset_target(work_root, "VisEvent")),
        (repo_root / "data" / "weights", dirs["weights"]),
        (repo_root / "data" / "official_results_E", dirs["official_results"]),
    ]
    for link, target in links:
        if target.exists():
            status["actions"].append({"action": "link", "link": str(link), "target": str(target), "status": make_junction(link, target)})
        else:
            status["actions"].append({"action": "link", "link": str(link), "target": str(target), "status": "target_missing"})

    status["actions"].extend(write_official_checkpoints(work_root, repo_root))
    status["elapsed_seconds"] = round(time.time() - started, 3)
    out = repo_root / "outputs" / "logs" / "data_setup_status.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    (dirs["logs"] / "data_setup_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
