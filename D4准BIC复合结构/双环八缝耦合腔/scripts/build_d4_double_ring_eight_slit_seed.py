# -*- coding: utf-8 -*-
from __future__ import print_function

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "coding" / "对角失谐准BIC寻优" / "run_fdtd_diagonal_detune_autosearch.py"


def main():
    spec = importlib.util.spec_from_file_location("d4_quasibic_search", str(SCRIPT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = module.save_seed_fsp()
    print("原始母版 FSP 已保存: {}".format(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
