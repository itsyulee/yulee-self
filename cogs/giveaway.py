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
import json
import os
import discord
from discord.ext import commands

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = os.path.join(bot.base_dir, 'config', 'giveaway_db.json')
        self.joined_ids = []
        self._load_state()
        
    def _load_state(self):
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                    self.joined_ids = data.get('joined_ids', [])
        except Exception:
            self.joined_ids = []
            
    def _save_state(self):
        if len(self.joined_ids) > 100:
            self.joined_ids = self.joined_ids[-100:]
        try:
            with open(self.db_path, 'w') as f:
                json.dump({'joined_ids': self.joined_ids}, f)
        except Exception as e:
            self.bot.log("ERROR", f"Failed to save giveaway DB: {e}")

    async def _process_message(self, message):
        cfg = self.bot.config.get('commands', {}).get('giveaway', {})
        if not cfg.get('enabled', False): 
            return

        raw_channels = cfg.get('channels', [])
        if isinstance(raw_channels, str):
            target_channels = [c.strip() for c in raw_channels.split(',') if c.strip().isdigit()]
        else:
            target_channels = [str(c) for c in raw_channels if str(c).strip().isdigit()]

        all_channels = [str(c) for c in self.bot.channels]
        if str(message.channel.id) not in all_channels:
            return

        if not message.embeds: return
        
        is_giveaway = False
        for embed in message.embeds:
            if embed.author and embed.author.name and " A New Giveaway Appeared!" in embed.author.name:
                is_giveaway = True
                break
        
        if not is_giveaway: return
        
        if message.id in self.joined_ids:
            return

        cooldown = cfg.get('cooldown', 2)
        await asyncio.sleep(cooldown)

        if not message.components: return
        
        try:
            component = message.components[0]
            if not isinstance(component, discord.ActionRow): return
            
            button = component.children[0]
            if isinstance(button, discord.Button) and not button.disabled:
                try:
                    await button.click()
                    self.joined_ids.append(message.id)
                    self._save_state()
                    self.bot.log("SUCCESS", f"Joined giveaway in {message.channel.name}")
                except Exception as e:
                    if "Did not receive a response" in str(e):
                         self.joined_ids.append(message.id)
                         self._save_state()
                         self.bot.log("SUCCESS", f"Joined giveaway in {message.channel.name}")
                    else:
                        self.bot.log("ERROR", f"Failed to join giveaway: {e}")
        except Exception as e:
            self.bot.log("ERROR", f"Failed to process giveaway: {e}")

    async def _safe_scan(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)
        
        sanitized_name = "".join(x for x in self.bot.username if x.isalnum())
        self.db_path = os.path.join(self.bot.base_dir, 'data', f'giveaway_db_{sanitized_name}.json')
        self._load_state()
        
        cfg = self.bot.config.get('commands', {}).get('giveaway', {})
        if not cfg.get('enabled', False): return

        raw_channels = cfg.get('channels', [])
        if isinstance(raw_channels, str):
            target_channels = [c.strip() for c in raw_channels.split(',') if c.strip().isdigit()]
        else:
            target_channels = [str(c) for c in raw_channels if str(c).strip().isdigit()]

        if not target_channels: return

        self.bot.log("SYS", f"Scanning for missed giveaways as {self.bot.username}...")
        
        for channel_id in target_channels:
            try:
                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                     try:
                        channel = await self.bot.fetch_channel(int(channel_id))
                     except Exception as e:
                        continue
                
                if channel:
                    permissions = channel.permissions_for(channel.guild.me)
                    if not permissions.read_messages or not permissions.read_message_history:
                        continue

                    try:
                        async for msg in channel.history(limit=20):
                             await self._process_message(msg)
                    except:
                        continue
                     
            except Exception as e:
                self.bot.log("ERROR", f"Error scanning channel {channel_id}: {e}")

    async def cog_load(self):
        self.bot.loop.create_task(self._safe_scan())

    @commands.Cog.listener()
    async def on_message(self, message):
        core_config = self.bot.config.get('core', {})
        monitor_id = str(core_config.get('monitor_bot_id', '408785106942164992'))
        if str(message.author.id) != monitor_id: return
        
        if not self.bot.is_ready(): return
        
        if self.bot.owo_user is None:
            self.bot.owo_user = message.author
        await self._process_message(message)

    async def register_actions(self):
        # giveaway is reactive
        pass

async def setup(bot):
    cog = Giveaway(bot)
    await bot.add_cog(cog)

