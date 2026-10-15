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
import random
import json
import os
import core.state as state
from discord.ext import commands

class LevelQuotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.quotes_file = os.path.join(self.bot.base_dir, 'data', 'neura_quotes.json')
        self.quotes = self._load_quotes()

    def _load_quotes(self):
        if os.path.exists(self.quotes_file):
            try:
                with open(self.quotes_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [q['quote'] for q in data.get('quotes', [])]
            except Exception as e:
                self.bot.log("ERROR", f"Failed to load quotes: {e}")
        return []

    def get_random_quote(self, min_len=10, max_len=100):
        eligible = [q for q in self.quotes if min_len <= len(q) <= max_len]
        if eligible:
            return random.choice(eligible)
        return random.choice(self.quotes) if self.quotes else "..."

    async def trigger_action_async(self):
        cfg = self.bot.config.get('level_grind', {})
        msg = self.get_random_quote(cfg.get('min_length', 10), cfg.get('max_length', 100))
        
        cooldown = cfg.get('cooldown', [60, 90])
        delay = random.uniform(cooldown[0], cooldown[1])
        
        uid = str(self.bot.user.id)
        if uid in state.account_stats:
            state.account_stats[uid]['level_quotes_sent'] = state.account_stats[uid].get('level_quotes_sent', 0) + 1
            
        return msg, delay

    def trigger_action(self):
        async def fetch_and_set():
            msg, delay = await self.trigger_action_async()
            if 'level_quotes' in self.bot.cmd_states:
                self.bot.cmd_states['level_quotes']['content'] = msg
                self.bot.cmd_states['level_quotes']['delay'] = delay
            
        asyncio.create_task(fetch_and_set())

    async def register_actions(self):
        cfg = self.bot.config.get('level_grind', {})
        if cfg.get('enabled', False):
            cooldown = cfg.get('cooldown', [60, 90])
            await self.bot.neura_register_command("level_quotes", "owo level", priority=self.bot.get_cmd_priority("level_quotes", 4), delay=random.uniform(cooldown[0], cooldown[1]), initial_offset=20)
            self.trigger_action()

async def setup(bot):
    await bot.add_cog(LevelQuotes(bot))