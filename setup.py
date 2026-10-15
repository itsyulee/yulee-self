# This file is part of YuleeSelf-UwU.
# Copyright (c) 2025-Present Routo
#
# YuleeSelf-UwU is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with YuleeSelf-UwU. If not, see <https://www.gnu.org/licenses/>.


"""
Author: zOnisdev
YuleeSelf-UwU - https://github.com/itsyulee/yulee-self
"""

import argparse
import os
from pathlib import Path


def main():
    os.chdir(Path(__file__).resolve().parent)
    parser = argparse.ArgumentParser(description='YULEESELF multi-user server setup')
    parser.add_argument('--quick', action='store_true', help='Install dependencies and start dashboard')
    parser.add_argument('--setup-only', action='store_true', help='Install dependencies without starting server')
    parser.add_argument('--repair', action='store_true', help='Repair installed dependencies')
    args = parser.parse_args()
    from yulee_engines.setup_engine import YuleeSetupEngine
    engine = YuleeSetupEngine()
    if not engine.run_full_setup(force_bootstrap=args.repair):
        raise SystemExit(1)
    if not args.setup_only:
        from service.gateway import serve
        serve()


if __name__ == '__main__':
    main()
