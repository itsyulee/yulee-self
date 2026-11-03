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
Author: Routo
YuleeSelf-UwU - https://github.com/itsyulee/yulee-self
"""


import os
import sys
import platform


def is_termux():
    if os.environ.get("TERMUX_VERSION"):
        return True
    if "com.termux" in os.environ.get("PREFIX", ""):
        return True
    return os.path.exists("/data/data/com.termux")


def get_platform():
    if is_termux():
        return "termux"
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "darwin":
        return "macos"
    return "linux"


def get_python_cmd():
    return sys.executable
