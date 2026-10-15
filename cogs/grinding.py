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



import discord
from discord.ext import commands
import asyncio
import random
import time
import re
import core.state as state
from utils import history_tracker as ht

class Grinding(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active = True
        self.cooldowns = {'hunt': 0, 'battle': 0, 'owo': 0}

        pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id != int(self.bot.owo_bot_id): return
        if self.bot.owo_user is None:
            self.bot.owo_user = message.author
        all_channels = [str(c) for c in self.bot.channels]
        if str(message.channel.id) not in all_channels:
            return
        content = message.content.lower()
        if not self.bot.is_message_for_me(message): return

        if "you found:" in content or "caught a" in content or "caught an" in content:
            if "hunt" in self.bot.cmd_states:
                cfg = self.bot.config.get('commands', {}).get('hunt', {})
                self.bot.cmd_states["hunt"]["delay"] = random.uniform(cfg.get('cooldown', [15, 18])[0], cfg.get('cooldown', [15, 18])[1])
        
        elif "you won" in content or "you lost" in content or "streak:" in content or "wins!" in content:
            if "battle" in self.bot.cmd_states:
                cfg = self.bot.config.get('commands', {}).get('battle', {})
                self.bot.cmd_states["battle"]["delay"] = random.uniform(cfg.get('cooldown', [15, 18])[0], cfg.get('cooldown', [15, 18])[1])

    async def register_actions(self):
        cfg_hunt = self.bot.config.get('commands', {}).get('hunt', {})
        if not cfg_hunt.get('enabled', False):
            self.bot.cmd_states.pop('hunt', None)
        if cfg_hunt.get('enabled', False):
            delay = random.uniform(cfg_hunt.get('cooldown', [15, 18])[0], cfg_hunt.get('cooldown', [15, 18])[1])
            rb_cfg = self.bot.config.get('reactionBot', {})
            if rb_cfg.get('enabled', False) and rb_cfg.get('hunt_and_battle', False):
                delay += 5
            await self.bot.neura_register_command("hunt", "hunt", priority=self.bot.get_cmd_priority("hunt", 3), delay=delay, initial_offset=5)

        cfg_battle = self.bot.config.get('commands', {}).get('battle', {})
        if not cfg_battle.get('enabled', False):
            self.bot.cmd_states.pop('battle', None)
        if cfg_battle.get('enabled', False):
            delay = random.uniform(cfg_battle.get('cooldown', [15, 18])[0], cfg_battle.get('cooldown', [15, 18])[1])
            rb_cfg = self.bot.config.get('reactionBot', {})
            if rb_cfg.get('enabled', False) and rb_cfg.get('hunt_and_battle', False):
                delay += 5
            await self.bot.neura_register_command("battle", "battle", priority=self.bot.get_cmd_priority("battle", 3), delay=delay, initial_offset=10)

        cfg_owo = self.bot.config.get('commands', {}).get('owo', {})
        if not cfg_owo.get('enabled', False):
            self.bot.cmd_states.pop('owo', None)
        if cfg_owo.get('enabled', False):
            delay = random.uniform(cfg_owo.get('cooldown', [10, 13])[0], cfg_owo.get('cooldown', [10, 13])[1])
            rb_cfg = self.bot.config.get('reactionBot', {})
            if rb_cfg.get('enabled', False) and rb_cfg.get('owo', False):
                delay += 5
            await self.bot.neura_register_command("owo", "owo", priority=self.bot.get_cmd_priority("owo", 1), delay=delay, initial_offset=15)

async def setup(bot):
    cog = Grinding(bot)
    await bot.add_cog(cog)