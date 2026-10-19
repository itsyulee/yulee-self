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

"""Run setup, then launch the web server through yulee.py.

Kept compatible with the existing Wispbyte startup command:
/usr/local/bin/python /home/container/setup.py
"""

import argparse
import os
from pathlib import Path
import traceback


def main():
    os.chdir(Path(__file__).resolve().parent)
    parser = argparse.ArgumentParser(description='YULEESELF multi-user server setup')
    parser.add_argument('--quick', action='store_true', help='Install dependencies and start dashboard')
    parser.add_argument('--setup-only', action='store_true', help='Install dependencies without starting server')
    parser.add_argument('--repair', action='store_true', help='Repair installed dependencies')
    args = parser.parse_args()

    print('[YULEESELF] Starting setup...', flush=True)
    try:
        from yulee_engines.setup_engine import YuleeSetupEngine
        engine = YuleeSetupEngine()
        if not engine.run_full_setup(force_bootstrap=args.repair):
            print('[YULEESELF] Setup FAILED. Check data/setup.log and the errors above.', flush=True)
            return 1
    except Exception:
        print('[YULEESELF] Setup FAILED with an exception:', flush=True)
        traceback.print_exc()
        return 1

    if args.setup_only:
        print('[YULEESELF] Setup completed (--setup-only); server not started.', flush=True)
        return 0

    print('[YULEESELF] Setup complete; launching web gateway...', flush=True)
    try:
        from yulee import main as run_server
        run_server()
    except Exception:
        print('[YULEESELF] Web startup FAILED:', flush=True)
        traceback.print_exc()
        print('[YULEESELF] On first run, set YULEESELF_ADMIN_USER and '
              'YULEESELF_ADMIN_PASSWORD in hosting environment settings.', flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
