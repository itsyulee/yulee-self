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

"""Start YULEESELF. Gateway is the single source of host/port settings."""

import os
from pathlib import Path


def configure_host():
    # Wispbyte/Pterodactyl may provide SERVER_PORT rather than PORT.
    for key in ('SERVER_PORT', 'PORT', 'YULEESELF_PORT'):
        value = os.environ.get(key, '').strip()
        if not value:
            continue
        try:
            port = int(value)
        except ValueError:
            raise ValueError(f'{key} must be a valid TCP port (got {value!r})') from None
        if not 1 <= port <= 65535:
            raise ValueError(f'{key} must be between 1 and 65535 (got {value!r})')
        break
    else:
        port = 8000

    os.environ['YULEESELF_HOST'] = '0.0.0.0'
    os.environ['PORT'] = str(port)
    print(f'[YULEESELF] Using web address 0.0.0.0:{port}', flush=True)
    return port


def main():
    os.chdir(Path(__file__).resolve().parent)
    configure_host()
    from service.gateway import serve
    serve()


if __name__ == '__main__':
    main()
