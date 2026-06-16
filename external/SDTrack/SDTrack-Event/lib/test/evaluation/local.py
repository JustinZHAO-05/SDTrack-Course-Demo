import os
from pathlib import Path

from lib.test.evaluation.environment import EnvSettings


def _repo_root():
    if os.environ.get('SDTRACK_REPO_ROOT'):
        return Path(os.environ['SDTRACK_REPO_ROOT']).resolve()
    return Path(__file__).resolve().parents[6]


def _repo_path(*parts):
    return str(_repo_root().joinpath(*parts))


def local_env_settings():
    settings = EnvSettings()

    # Set your local paths here.

    settings.davis_dir = ''
    settings.got10k_lmdb_path = '/data/dataset/got10k_lmdb'
    settings.got10k_path = '/data/dataset/got10k'
    settings.got_packed_results_path = ''
    settings.got_reports_path = ''
    settings.itb_path = '/data/dataset/itb'
    settings.lasot_extension_subset_path_path = '/data/dataset/lasot_extension_subset'
    settings.lasot_lmdb_path = '/data/dataset/lasot_lmdb'
    settings.lasot_path = '/data/dataset/lasot'
    settings.network_path = os.environ.get('SDTRACK_NETWORK_PATH', _repo_path('data', 'weights'))    # Where tracking networks are stored.
    settings.nfs_path = '/data/dataset/nfs'
    settings.otb_path = '/data/dataset/otb'
    settings.prj_dir = os.environ.get('SDTRACK_PRJ_DIR', _repo_path('external', 'SDTrack', 'SDTrack-Event'))
    settings.result_plot_path = os.environ.get('SDTRACK_RESULT_PLOT_PATH', _repo_path('outputs', 'test', 'result_plots'))
    settings.results_path = os.environ.get('SDTRACK_RESULTS_PATH', _repo_path('outputs', 'test', 'tracking_results'))    # Where to store tracking results
    settings.save_dir = os.environ.get('SDTRACK_SAVE_DIR', _repo_path('outputs'))
    settings.segmentation_path = os.environ.get('SDTRACK_SEGMENTATION_PATH', _repo_path('outputs', 'test', 'segmentation_results'))
    settings.tc128_path = '/data/dataset/TC128'
    settings.tn_packed_results_path = ''
    settings.tnl2k_path = '/data/dataset/tnl2k'
    settings.tpl_path = ''
    settings.trackingnet_path = '/data/dataset/trackingnet'
    settings.uav_path = '/data/dataset/uav'
    settings.vot18_path = '/data/dataset/vot2018'
    settings.vot22_path = '/data/dataset/vot2022'
    settings.vot_path = '/data/dataset/VOT2019'
    settings.youtubevos_dir = ''
    settings.eotb_path = os.environ.get('SDTRACK_EOTB_PATH', _repo_path('data', 'FE108', 'test'))
    settings.visevent_path = os.environ.get('SDTRACK_VISEVENT_PATH', _repo_path('data', 'VisEvent', 'test'))
    settings.felt_path = os.environ.get('SDTRACK_FELT_PATH', _repo_path('data', 'FELT', 'test'))
    return settings

