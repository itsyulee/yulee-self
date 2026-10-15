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


def main():
    os.chdir(Path(__file__).resolve().parent)
    from service.gateway import serve
    serve()


if __name__ == '__main__':
    main()
