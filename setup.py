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
import subprocess
import sys
import venv
from importlib.metadata import PackageNotFoundError, version


def requirements_ready(path):
    """Check installed versions without importing NumPy or any application code."""
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith(('#', '-')):
            continue
        name, expected = line.split('==', 1)
        try:
            if version(name.strip()) != expected.strip():
                return False
        except PackageNotFoundError:
            return False
    return True


def prepare_runtime(root, repair=False):
    """Always run setup and the dashboard in this project's isolated environment."""
    if sys.version_info < (3, 12):
        raise RuntimeError('Python 3.12 or newer is required; Python 3.14 is supported.')
    environment = root / '.venv'
    executable = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    in_environment = Path(sys.prefix).resolve() == environment.resolve()
    if not in_environment or not sys.flags.no_user_site:
        if not executable.is_file():
            print('[YULEESELF] Preparing runtime...', flush=True)
            venv.EnvBuilder(with_pip=True).create(environment)
        env = os.environ.copy()
        env['PYTHONNOUSERSITE'] = '1'
        env.pop('PYTHONPATH', None)
        return subprocess.call([str(executable), '-s', str(root / 'setup.py'), *sys.argv[1:]],
                               cwd=root, env=env)

    requirements = root / 'requirements.txt'
    if repair or not requirements_ready(requirements):
        print('[YULEESELF] Installing requirements.txt...', flush=True)
        subprocess.run([sys.executable, '-m', 'ensurepip', '--upgrade'], check=True)
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip',
                        '--index-url', 'https://pypi.org/simple'], check=True)
        command = [sys.executable, '-m', 'pip', 'install', '--upgrade', '--no-cache-dir',
                   '--index-url', 'https://pypi.org/simple', '-r', str(requirements)]
        if repair:
            command.append('--force-reinstall')
        subprocess.run(command, check=True)
        subprocess.run([sys.executable, '-m', 'pip', 'check'], check=True)
    return None


def main():
    os.chdir(Path(__file__).resolve().parent)
    parser = argparse.ArgumentParser(description='YULEESELF multi-user server setup')
    parser.add_argument('--quick', action='store_true', help='Install dependencies and start dashboard')
    parser.add_argument('--setup-only', action='store_true', help='Install dependencies without starting server')
    parser.add_argument('--repair', action='store_true', help='Repair installed dependencies')
    args = parser.parse_args()

    try:
        result = prepare_runtime(Path(__file__).resolve().parent, repair=args.repair)
        if result is not None:
            return result
        print('[YULEESELF] Starting setup...', flush=True)
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
