# This file is part of NeuraSelf-UwU.
# Copyright (c) 2025-Present Routo
#
# NeuraSelf-UwU is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with NeuraSelf-UwU. If not, see <https://www.gnu.org/licenses/>.


"""
Author: Routo
NeuraSelf-UwU - https://github.com/routo-loop/neura-self
"""

import re

def parse_embed(fields):
    dealer_points = None
    player_points = None
    is_soft = False

    for field in fields:
        name = field.name or ""
        d_match = re.search(r'Dealer\s*`?\[(\d+)(?:\+\?)?\]`?', name)
        if d_match:
            dealer_points = int(d_match.group(1))
            continue

        p_match = re.search(r'`?\[(\d+)\](\*?)`?', name)
        if p_match:
            player_points = int(p_match.group(1))
            is_soft = bool(p_match.group(2))
            continue

    return dealer_points, player_points, is_soft


def get_best_move(dealer_card, player_total, is_soft):
    """basic strategy but i think good enough to choose correct move"""
    if is_soft:
        if player_total <= 17:
            return "HIT"
        if player_total == 18:
            if dealer_card >= 9:
                return "HIT"
            return "STAND"
        return "STAND"

    if player_total <= 11:
        return "HIT"
    if player_total == 12:
        return "STAND" if 4 <= dealer_card <= 6 else "HIT"
    if 13 <= player_total <= 16:
        return "STAND" if 2 <= dealer_card <= 6 else "HIT"
    return "STAND"