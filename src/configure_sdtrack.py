"""Write this project's own local path adapter into a separately installed SDTrack."""
from pathlib import Path
import subprocess

COMMIT = "a3e4d8d508e1808e9e41629733b20d38ee52ce05"


def main():
    root = Path(__file__).resolve().parents[1]
    upstream = root / "external" / "SDTrack"
    if not (upstream / ".git").exists():
        raise SystemExit("Clone the official SDTrack repository at the version in README.md first.")
    actual = subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
    if actual != COMMIT:
        raise SystemExit(f"Expected upstream commit {COMMIT}, got {actual}.")
    event = upstream / "SDTrack-Event"
    config = {
        "prj_dir": str(event), "save_dir": str(root / "outputs"),
        "network_path": str(root / "data" / "weights"),
        "results_path": str(root / "outputs/test/tracking_results"),
        "result_plot_path": str(root / "outputs/test/result_plots"),
        "segmentation_path": str(root / "outputs/test/segmentation_results"),
        "eotb_path": str(root / "data/FE108/test"),
        "visevent_path": str(root / "data/VisEvent/test"),
    }
    code = "from lib.test.evaluation.environment import EnvSettings\n\ndef local_env_settings():\n    settings = EnvSettings()\n"
    code += "".join(f"    settings.{key} = {value!r}\n" for key, value in config.items())
    code += "    return settings\n"
    target = event / "lib/test/evaluation/local.py"
    target.write_text(code, encoding="utf-8")
    train = {"workspace_dir": str(event), "tensorboard_dir": str(root / "outputs/tensorboard"), "pretrained_networks": str(root / "data/weights"), "eotb_dir_train": str(root / "data/FE108/train"), "visevent_train": str(root / "data/VisEvent/train")}
    code = "class EnvironmentSettings:\n    def __init__(self):\n" + "".join(f"        self.{key} = {value!r}\n" for key, value in train.items())
    (event / "lib/train/admin/local.py").write_text(code, encoding="utf-8")
    print("Wrote local project paths to the separately installed SDTrack checkout.")


if __name__ == "__main__":
    main()
