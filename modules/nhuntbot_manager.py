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


import math
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class TraitSpec:
    name: str
    inc: float
    power: float
    max_lvl: int
    base_prio: int

class HuntBotManager:
    """
    i found this method and i think it is good fit with huntbot use it
    This implements the 'Meta Strategy' where traits are upgraded in 
    stages to maximize profit and reach 24h duration goals.
    """
    def __init__(self):
        self.specs = {
            "efficiency": TraitSpec("Efficiency", 10.0, 1.748, 215, 8),
            "duration":   TraitSpec("Duration", 10.0, 1.7, 235, 4),
            "cost":       TraitSpec("Cost", 1000.0, 3.4, 5, 10),
            "gain":       TraitSpec("Gain", 10.0, 1.8, 200, 8),
            "exp":        TraitSpec("Exp", 10.0, 1.8, 200, 3),
            "radar":      TraitSpec("Radar", 50.0, 2.5, 999, 1)
        }

    def _get_dynamic_prio(self, trait: str, levels: Dict[str, int], config: Dict) -> int:
        """ if any dev reviewing code so i try to explain this function :
        there are 3 rules which i think good for huntbot , and i explained below"""

        spec = self.specs[trait]
        user_prio = config.get('priorities', {}).get(trait, spec.base_prio)
        
        # meta rule 1: Keep efficiency and Gain leveled together
        if trait in ["efficiency", "gain"]:
            other = "gain" if trait == "efficiency" else "efficiency"
            if levels[trait] < levels[other]:
                return user_prio + 2
        
        # meta rule 2: duration focus if below target (default 12h ~ 125 level)
        if trait == "duration" and levels[trait] < config.get('target_duration_lvl', 125):
            return user_prio + 3

        # meta rule 3: exp focus after Gain/Eff are maxed
        if trait == "exp" and levels["efficiency"] >= 215 and levels["gain"] >= 200:
            return 10

        return user_prio

    def allocate(self, essence: int, levels: Dict[str, int], invested: Dict[str, int], enabled: List[str], config: Dict = {}) -> Dict[str, int]:
        if not config.get('enabled', True):
            return {}

        allocation = {t: 0 for t in enabled}
        remaining = essence
        curr_lvls = levels.copy()
        curr_inv = invested.copy()

        while remaining > 0:
            best_trait, best_ratio, best_cost = None, -1.0, 0

            for t_name in enabled:
                spec = self.specs.get(t_name)
                if not spec or curr_lvls[t_name] >= spec.max_lvl:
                    continue

                cost = int(spec.inc * ((curr_lvls[t_name] + 1) ** spec.power))
                required = max(0, cost - curr_inv.get(t_name, 0))
                
                if required <= 0:
                    curr_lvls[t_name] += 1
                    curr_inv[t_name] = 0
                    continue

                prio = self._get_dynamic_prio(t_name, curr_lvls, config)
                ratio = prio / required

                if required <= remaining and ratio > best_ratio:
                    best_ratio, best_trait, best_cost = ratio, t_name, required

            if best_trait:
                allocation[best_trait] += best_cost
                remaining -= best_cost
                curr_lvls[best_trait] += 1
                curr_inv[best_trait] = 0
            else:
                target = max(enabled, key=lambda t: self._get_dynamic_prio(t, curr_lvls, config) / 
                            max(1, int(self.specs[t].inc * ((curr_lvls[t]+1)**self.specs[t].power)) - curr_inv.get(t,0)))
                allocation[target] = allocation.get(target, 0) + remaining
                break

        return {t: amt for t, amt in allocation.items() if amt > 0}

manager = HuntBotManager()
