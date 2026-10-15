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
import json
import random
import core.state as state
from discord.ext import commands

class Others(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.zoo = False
        self.emoji_dict = {}
        
        try:
            with open("utils/emojis.json", 'r', encoding="utf-8") as file:
                self.emoji_dict = json.load(file)
        except:
            pass

    def get_emoji_names(self, text):
        pattern = re.compile(r"<a:[a-zA-Z0-9_]+:[0-9]+>|:[a-zA-Z0-9_]+:|[\U0001F300-\U0001F6FF\U0001F700-\U0001F77F]")
        emojis = pattern.findall(text)
        return [self.emoji_dict[char]["name"] for char in emojis if char in self.emoji_dict]

    async def _auto_accept_rules(self, message):
        all_channels = [str(c) for c in self.bot.channels]
        if str(message.channel.id) not in all_channels:
            return

        content = message.content.lower()
        if "**you must accept these rules to use the bot!**" in content:
            if message.components:
                await asyncio.sleep(random.uniform(0.6, 1.7))
                try:
                    comp = message.components[0]
                    if hasattr(comp, 'children'):
                        btn = comp.children[0]
                        if not btn.disabled:
                            await btn.click()
                            self.bot.log("SUCCESS", "Auto-Accepted OwO Rules")
                except Exception as e:
                    self.bot.log("ERROR", f"Failed to accept rules: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        await self._auto_accept_rules(message)

        monitor_id = str(self.bot.config.get('core', {}).get('monitor_bot_id', '408785106942164992'))
        if str(message.author.id) != monitor_id:
            return
        
        if self.bot.owo_user is None:
            self.bot.owo_user = message.author
        
        all_channels = [str(c) for c in self.bot.channels]
        if str(message.channel.id) not in all_channels:
            return

        content = message.content.lower()
        
        if "you currently have" in content and "cowoncy" in content:
            if not self.bot.is_message_for_me(message, role="header"):
                return
            try:
                cash_match = re.search(r'you currently have[^\d]*(\d{1,3}(?:,\d{3})*)', message.content.lower())
                if cash_match:
                    cash_str = cash_match.group(1).replace(',', '')
                    is_initial = self.bot.stats['current_cash'] is None
                    self.bot.stats['current_cash'] = int(cash_str)
                    self.bot.stats['last_cash_update'] = time.time()
                    state.record_snapshot(self.bot.user_id)
                    if is_initial:
                        self.bot.log("SYS", f"Initial Cash Balance synced: {cash_str} cowoncy")
                    else:
                        self.bot.log("INFO", f"Cash Updated: {cash_str} cowoncy")
            except:
                pass


        elif "you do not have an active battle team" in content:
            if not self.bot.is_message_for_me(message):
                return
            self.zoo = True
            await self.bot.neura_enqueue("zoo", priority=2)
            self.bot.log("SYS", "Zoo triggered")

        elif "'s zoo! **" in content and self.zoo:
            if not self.bot.is_message_for_me(message, role="header"):
                return
            animals = self.get_emoji_names(message.content)
            animals.reverse()
            self.zoo = False
            
            for i in range(min(len(animals), 3)):
                await self.bot.neura_enqueue(f"team add {animals[i]}", priority=2)
                self.bot.log("CMD", f"Added animal: {animals[i]}")

    async def register_actions(self):
        pass

async def setup(bot):
    cog = Others(bot)
    await bot.add_cog(cog)
