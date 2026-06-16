from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def run(command: list[str]) -> dict[str, str | int]:
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
        return {"returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}
    except Exception as exc:
        return {"returncode": -1, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a reproducibility environment report.")
    parser.add_argument("--out", default="outputs/logs/environment_report.json")
    args = parser.parse_args()
    report = {
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "commands": {
            "nvidia-smi": run(["nvidia-smi"]) if shutil.which("nvidia-smi") else {"returncode": -1, "stdout": "", "stderr": "not found"},
            "git": run(["git", "--version"]) if shutil.which("git") else {"returncode": -1, "stdout": "", "stderr": "not found"},
            "uv": run(["uv", "--version"]) if shutil.which("uv") else {"returncode": -1, "stdout": "", "stderr": "not found"},
            "xelatex": run(["xelatex", "--version"]) if shutil.which("xelatex") else {"returncode": -1, "stdout": "", "stderr": "not found"},
            "pdftoppm": run(["pdftoppm", "-v"]) if shutil.which("pdftoppm") else {"returncode": -1, "stdout": "", "stderr": "not found"},
            "torch": run([sys.executable, "-c", "import torch; print(torch.__version__, torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO_CUDA')"]),
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
