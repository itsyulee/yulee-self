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



import asyncio
import time
import re
import random
import core.state as state
from discord.ext import commands

class NeuraGems(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active = True
        
        self.gem_tiers = {
            "fabled": ["057", "071", "078", "085"],
            "legendary": ["056", "070", "077", "084"],
            "mythical": ["055", "069", "076", "083"],
            "epic": ["054", "068", "075", "082"],
            "rare": ["053", "067", "074", "081"],
            "uncommon": ["052", "066", "073", "080"],
            "common": ["051", "065", "072", "079"],
        }
        
        self.inventory_check = False
        self.last_inv_time = 0

    def convert_small_numbers(self, text):
        mapping = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
        nums = "".join(filter(str.isdigit, text.translate(mapping)))
        return int(nums) if nums else 0

    def find_gems_available(self, content):
        matches = re.findall(r"(?:`|\*\*)?(\d{2,3})(?:`|\*\*)?.*?([⁰¹²³⁴⁵⁶⁷⁸⁹0-9]+)", content)
        available = {}
        for gid, count_str in matches:
            if gid.isdigit(): 
                available[gid] = self.convert_small_numbers(count_str)
        return available

    def find_gems_to_use(self, available, target_types=None):
        cnf = self.bot.config.get('commands', {}).get('gems', {})
        tier_cfg = cnf.get('tiers', {})
        type_cfg = cnf.get('types', {})
        order_cfg = cnf.get('order', {})
        use_set = cnf.get('use_gems_set', False)

        tier_priority = ['fabled', 'legendary', 'mythical', 'epic', 'rare', 'uncommon', 'common']
        if order_cfg.get('lowestToHighest', False):
            tier_priority.reverse()

        desired_types = []
        if target_types:
            desired_types = target_types
        else:
            if type_cfg.get('huntGem', True): desired_types.append('huntGem')
            if type_cfg.get('empoweredGem', True): desired_types.append('empoweredGem')
            if type_cfg.get('luckyGem', True): desired_types.append('luckyGem')
            if type_cfg.get('specialGem', False): desired_types.append('specialGem')

        type_to_index = {
            "huntGem": 0,
            "empoweredGem": 1, 
            "luckyGem": 2,
            "specialGem": 3
        }

        if use_set:
            for tier in tier_priority:
                if not tier_cfg.get(tier, True): continue
                
                tier_ids = self.gem_tiers.get(tier)
                if not tier_ids: continue

                has_all_in_tier = True
                temp_selection = []
                
                for g_type in desired_types:
                    idx = type_to_index.get(g_type)
                    if idx is None or idx >= len(tier_ids): 
                        has_all_in_tier = False
                        break
                    
                    gem_id = tier_ids[idx]
                    if available.get(gem_id, 0) < 1:
                        has_all_in_tier = False
                        break
                    temp_selection.append(gem_id)
                
                if has_all_in_tier:
                    for g in temp_selection:
                        available[g] -= 1
                    return temp_selection

        gems_to_equip = []
        for g_type in desired_types:
            idx = type_to_index.get(g_type)
            if idx is None: continue

            for tier in tier_priority:
                if not tier_cfg.get(tier, True): continue
                
                tier_ids = self.gem_tiers.get(tier)
                if not tier_ids or idx >= len(tier_ids): continue
                
                gem_id = tier_ids[idx]
                if available.get(gem_id, 0) > 0:
                    gems_to_equip.append(gem_id)
                    available[gem_id] -= 1
                    break
        
        return gems_to_equip if gems_to_equip else None

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id != 408785106942164992:
            return
        
        cfg = self.bot.config.get('commands', {}).get('gems', {})
        if not cfg.get('enabled', True):
            return

        all_channels = [str(c) for c in self.bot.channels]
        if str(message.channel.id) not in all_channels:
            return

        content = message.content.lower()
        is_for_me = self.bot.is_message_for_me(message)
        
        if not is_for_me and (time.time() - self.bot.last_sent_time) < 5:
             if "hunt" in self.bot.last_sent_command.lower() or "inv" in self.bot.last_sent_command.lower() or "gems" in self.bot.last_sent_command.lower():
                 is_for_me = True

        if not is_for_me:
            return

        if "caught" in content and "spent" in content and "hunt is empowered by" not in content:
            now = time.time()
            if now - self.last_inv_time > 15:
                cnf = self.bot.config.get('commands', {}).get('gems', {})
                type_cfg = cnf.get('types', {})
                st = self.bot.stats
                force_lucky = st.get('force_lucky_gems', False)
                
                missing_types = []
                if type_cfg.get('huntGem', True): missing_types.append('huntGem')
                if type_cfg.get('empoweredGem', True): missing_types.append('empoweredGem')
                if type_cfg.get('luckyGem', True) or force_lucky: missing_types.append('luckyGem')
                if type_cfg.get('specialGem', False): missing_types.append('specialGem')
                
                if missing_types:
                    actually_missing = [t for t in missing_types if t not in state.missing_gems_cache.get(self.bot.user_id, [])]
                    
                    if actually_missing:
                        if state.checking_gems.get(self.bot.user_id):
                            return

                        self.bot.log("SYS", "[NeuraGems] No active gems detected! Triggering inventory check.")
                        state.checking_gems[self.bot.user_id] = {
                            "time": time.time(),
                            "types": actually_missing
                        }
                        self.last_inv_time = now
                        await self.bot.neura_enqueue("owo inv", priority=2)
            return

        activation_match = re.search(r":(\w+): \| .* activated a\(n\) (.*) gem!", content)
        if activation_match:
            gem_emoji = activation_match.group(1)
            gem_name = activation_match.group(2).lower()
            
            g_type = None
            if "empowering" in gem_name: g_type = "empoweredGem"
            elif "hunting" in gem_name: g_type = "huntGem"
            elif "lucky" in gem_name: g_type = "luckyGem"
            elif "special" in gem_name: g_type = "specialGem"
            
            if g_type:
                if self.bot.user_id not in state.missing_gems_cache:
                    state.missing_gems_cache[self.bot.user_id] = []
                
                if g_type in state.missing_gems_cache[self.bot.user_id]:
                    state.missing_gems_cache[self.bot.user_id].remove(g_type)
                
                self.bot.log("SUCCESS", f"[NeuraGems] Confirmation: {g_type} activated. Cache updated.")

                self.last_inv_time = time.time()
                state.checking_gems[self.bot.user_id] = False
                return

        if "hunt is empowered by" in content:
            active_gems = []
            if "gem1" in content: active_gems.append("huntGem")
            if "gem3" in content: active_gems.append("empoweredGem")
            if "gem4" in content: active_gems.append("luckyGem")
            if "star" in content: active_gems.append("specialGem")

            cnf = self.bot.config.get('commands', {}).get('gems', {})
            type_cfg = cnf.get('types', {})
            st = self.bot.stats
            force_lucky = st.get('force_lucky_gems', False)
            
            missing_types = []
            if type_cfg.get('huntGem', True) and "huntGem" not in active_gems: missing_types.append("huntGem")
            if type_cfg.get('empoweredGem', True) and "empoweredGem" not in active_gems: missing_types.append("empoweredGem")
            
            if (type_cfg.get('luckyGem', True) or force_lucky) and "luckyGem" not in active_gems: 
                missing_types.append("luckyGem")
                
            if type_cfg.get('specialGem', False) and "specialGem" not in active_gems: missing_types.append("specialGem")

            if missing_types:
                actually_missing = [t for t in missing_types if t not in state.missing_gems_cache.get(self.bot.user_id, [])]
                
                if actually_missing:
                    if state.checking_gems.get(self.bot.user_id):
                        return

                    self.bot.log("SYS", f"[NeuraGems] Active gems detected, but missing: {', '.join(actually_missing)}. Checking inventory...")
                    state.checking_gems[self.bot.user_id] = {
                        "time": time.time(),
                        "types": actually_missing
                    }
                    await self.bot.neura_enqueue("owo inv", priority=2)
                else:
                    pass
            return

        if ("'s inventory" in content or "'s gems" in content) and "**" in content:
             if state.checking_gems.get(self.bot.user_id):
                if not self.bot.is_message_for_me(message, role="header"):
                    if not self.bot.is_message_for_me(message):
                        return

                gem_info = state.checking_gems.get(self.bot.user_id, {})
                missing_types = gem_info.get("types", ["huntGem", "empoweredGem", "luckyGem"])

                state.checking_gems[self.bot.user_id] = False
                
                available = self.find_gems_available(message.content)
                to_use = self.find_gems_to_use(available, target_types=missing_types)

                if self.bot.user_id not in state.missing_gems_cache:
                    state.missing_gems_cache[self.bot.user_id] = []
                

                type_to_index = {
                    "huntGem": 0,
                    "empoweredGem": 1, 
                    "luckyGem": 2,
                    "specialGem": 3
                }
                
  
                cnf = self.bot.config.get('commands', {}).get('gems', {})
                type_cfg = cnf.get('types', {})
                tier_cfg = cnf.get('tiers', {})
                
                all_enabled_types = []
                if type_cfg.get('huntGem', True): all_enabled_types.append('huntGem')
                if type_cfg.get('empoweredGem', True): all_enabled_types.append('empoweredGem')
                if type_cfg.get('luckyGem', True): all_enabled_types.append('luckyGem')
                if type_cfg.get('specialGem', False): all_enabled_types.append('specialGem')

                for g_type in all_enabled_types:
                    idx = type_to_index.get(g_type)
                    if idx is None: continue
                    
                    tier_priority = ['fabled', 'legendary', 'mythical', 'epic', 'rare', 'uncommon', 'common']
                    has_any = False
                    for tier in tier_priority:
                        if not tier_cfg.get(tier, True): continue 
                        tier_ids = self.gem_tiers.get(tier)
                        if not tier_ids or idx >= len(tier_ids): continue
                        gem_id = tier_ids[idx]
                        if available.get(gem_id, 0) > 0:
                            has_any = True
                            break
                    
                    if has_any:
                        if g_type in state.missing_gems_cache[self.bot.user_id]:
                            state.missing_gems_cache[self.bot.user_id].remove(g_type)
                            self.bot.log("SYS", f"[NeuraGems] {g_type} found in inventory, removed from missing cache.")
                    else:
                        if g_type not in state.missing_gems_cache[self.bot.user_id]:
                            state.missing_gems_cache[self.bot.user_id].append(g_type)
                            self.bot.log("WARN", f"[NeuraGems] {g_type} not found in inventory, added to missing cache.")

                if to_use:
                    cmd_ids = [gid if not gid.startswith('0') else gid[1:] for gid in to_use]
                    use_cmd = f"owo use {' '.join(cmd_ids)}"
                    uid = str(self.bot.user_id)
                    if uid in state.account_stats:
                        st = state.account_stats[uid]
                        st['gems_used'] = st.get('gems_used', 0) + len(to_use)
                        state.save_account_stats()
                    await self.bot.neura_enqueue(use_cmd, priority=2)
                    self.bot.log("SUCCESS", f"[NeuraGems] Equipped: {use_cmd}")
                    self.last_inv_time = time.time()
                else:
                    self.bot.log("WARN", f"[NeuraGems] Inventory checked, but no matching gems found for: {missing_types}")

    async def register_actions(self):
        pass

async def setup(bot):
    cog = NeuraGems(bot)
    bot.add_listener(cog.on_message, 'on_message')
    await bot.add_cog(cog)
