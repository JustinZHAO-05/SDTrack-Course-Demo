import os
from pathlib import Path


class EnvironmentSettings:
    def __init__(self):
        repo_root = Path(__file__).resolve().parents[6]
        sdtrack_root = repo_root / "external" / "SDTrack" / "SDTrack-Event"
        data_root = Path(os.environ.get("SDTRACK_DATA_ROOT", repo_root / "data")).resolve()
        outputs_root = Path(os.environ.get("SDTRACK_OUTPUT_ROOT", repo_root / "outputs")).resolve()

        self.workspace_dir = str(sdtrack_root)    # Base directory for saving network checkpoints.
        self.tensorboard_dir = str(outputs_root / "tensorboard")    # Directory for tensorboard files.
        self.pretrained_networks = str(data_root / "weights")
        self.lasot_dir = '/data/dataset/lasot'
        self.got10k_dir = '/data/dataset/got10k/train'
        self.got10k_val_dir = '/data/dataset/got10k/val'
        self.lasot_lmdb_dir = '/data/dataset/lasot_lmdb'
        self.got10k_lmdb_dir = '/data/dataset/got10k_lmdb'
        self.trackingnet_dir = '/data/dataset/trackingnet'
        self.trackingnet_lmdb_dir = '/data/dataset/trackingnet_lmdb'
        self.coco_dir = '/data/dataset/coco'
        self.coco_lmdb_dir = '/data/dataset/coco_lmdb'
        self.lvis_dir = ''
        self.sbd_dir = ''
        self.imagenet_dir = '/data/dataset/vid'
        self.imagenet_lmdb_dir = '/data/dataset/vid_lmdb'
        self.imagenetdet_dir = ''
        self.ecssd_dir = ''
        self.hkuis_dir = ''
        self.msra10k_dir = ''
        self.davis_dir = ''
        self.youtubevos_dir = ''
        self.eotb_dir_train = str(data_root / "FE108" / "train")
        self.visevent_train = str(data_root / "VisEvent" / "train")
        self.felt_train = str(data_root / "FELT" / "train")
