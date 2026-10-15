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
from discord.ext import commands

class AutoOpen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active = True
        self.cooldowns = {
            'crate': 0.0,
            'lootbox': 0.0
        }

    async def _send_cmd(self, cmd_name):
        cfg = self.bot.config.get('commands', {}).get('open', {})
        sub_cfg = cfg.get(cmd_name, {})
        amt = sub_cfg.get('type', 'all')
        
        amt_str = str(amt).strip().lower()
        suffix = 'all' if amt_str in ['', 'all'] else str(amt)
        content = f"{cmd_name} {suffix}"
        
        await self.bot.neura_enqueue(content, priority=4)
        return True

    @commands.Cog.listener()
    async def on_message(self, message):
        monitor_id = str(self.bot.config.get('core', {}).get('monitor_bot_id', '408785106942164992'))
        if str(message.author.id) != monitor_id:
            return
        if self.bot.owo_user is None:
            self.bot.owo_user = message.author
            
        all_channels = [str(c) for c in self.bot.channels]
        if str(message.channel.id) not in all_channels:
            return
            
        cfg = self.bot.config.get('commands', {}).get('open', {})
        if not cfg.get('enabled', True):
            return

        use_crate = cfg.get('crate', {}).get('enabled', False)
        use_lootbox = cfg.get('lootbox', {}).get('enabled', False)
        lower = message.content.lower()

        if ("received a" in lower or "found a" in lower) and "weapon crate" in lower:
            if use_crate and time.time() >= self.cooldowns['crate']:
                self.cooldowns['crate'] = time.time() + 10
                await asyncio.sleep(1.2)
                await self._send_cmd("crate")

        if ("received a" in lower or "found a" in lower) and "lootbox" in lower:
            if use_lootbox and time.time() >= self.cooldowns['lootbox']:
                self.cooldowns['lootbox'] = time.time() + 10
                await asyncio.sleep(1.2)
                await self._send_cmd("lootbox")

        if "you don't have any lootboxes" in lower or "no lootboxes" in lower:
            self.cooldowns['lootbox'] = time.time() + 3600
            self.bot.log("COOLDOWN", "Lootbox not available. Pausing 1h.")

        if "you don't have any crates" in lower or "no weapon crates" in lower:
            self.cooldowns['crate'] = time.time() + 86400
            self.bot.log("COOLDOWN", "Crate not available. Pausing 24h.")

        if "resets in" in lower and "weapon crate" in lower:
            h = re.search(r'(\d+)\s*h', lower)
            m = re.search(r'(\d+)\s*m', lower)
            s = re.search(r'(\d+)\s*s', lower)
            total = 0
            if h: total += int(h.group(1)) * 3600
            if m: total += int(m.group(1)) * 60
            if s: total += int(s.group(1))
            if total > 0:
                self.cooldowns['crate'] = time.time() + total + 10

    async def register_actions(self):
        pass

async def setup(bot):
    cog = AutoOpen(bot)
    await bot.add_cog(cog)