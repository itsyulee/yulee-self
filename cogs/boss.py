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
import time
import random

from component_v2_neura import parse_v2_message, get_boss_battle_id
import json
import os
import re

class Boss(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.state_file = "data/boss_state.json"
        self._load_state()
        self.enabled = self.bot.config.get("boss", {}).get("enabled", True)
        self.join_chance = self.bot.config.get("boss", {}).get("join_chance", 100)
        self.join_all = self.bot.config.get("boss", {}).get("join_all_guilds", True)
        self.ignore_guilds = [str(g) for g in self.bot.config.get("boss", {}).get("ignore_guilds", [])]
        self.playing_guild_ids = set()
        self._update_playing_guilds()

    def _update_playing_guilds(self):
        self.playing_guild_ids.clear()
        for c_id in self.bot.channels:
            ch = self.bot.get_channel(int(c_id))
            if ch and ch.guild:
                self.playing_guild_ids.add(str(ch.guild.id))
        
        if hasattr(self.bot, 'guild_id') and self.bot.guild_id:
            self.playing_guild_ids.add(str(self.bot.guild_id))

    async def register_actions(self):
        cfg = self.bot.config.get("boss", {})
        self.enabled = cfg.get("enabled", True)
        self.join_chance = cfg.get("join_chance", 100)
        self.join_all = cfg.get("join_all_guilds", True)
        self.ignore_guilds = [str(g) for g in cfg.get("ignore_guilds", [])]
        self._update_playing_guilds()
        self.bot.log("SYS", f"Boss Battle settings refreshed. Tracking {len(self.playing_guild_ids)} guilds.")

    def _load_state(self):
        self.tickets = 3
        self.last_reset = 0
        self.joined_ids = set()
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    self.tickets = data.get("tickets", 3)
                    self.last_reset = data.get("last_reset", 0)
                    self.joined_ids = set(data.get("joined_ids", []))
            except: pass

    def _save_state(self):
        try:
            with open(self.state_file, "w") as f:
                json.dump({
                    "tickets": self.tickets,
                    "last_reset": self.last_reset,
                    "joined_ids": list(self.joined_ids)
                }, f)
        except: pass

    def _check_reset(self):
        now = time.time()
        if now - self.last_reset > 72000: 
            self.tickets = 3
            self.last_reset = now
            self.joined_ids.clear()
            self._save_state()

    @commands.Cog.listener()
    async def on_message(self, message):
        if str(message.author.id) != self.bot.owo_bot_id:
            return
        if message.channel.id != self.bot.channel_id:
            return

        if not self.bot.is_message_for_me(message):
            return

        full_content = self.bot.get_full_content(message)
        sync_happened = False
        if "you currently have" in full_content and "/3 boss ticket" in full_content:
            match = re.search(r'(\d+)/3 boss ticket', full_content)
            if match:
                self.tickets = int(match.group(1))
                self.last_reset = time.time()
                sync_happened = True
        elif "ran out of boss tickets" in full_content:
            self.tickets = 0
            self.last_reset = time.time()
            sync_happened = True
            
        if sync_happened:
            self.bot.log("BOSS", f"Synced tickets with OwO: {self.tickets}/3")
            self._save_state()

    @commands.Cog.listener()
    async def on_socket_raw_receive(self, msg):
        if not self.enabled or self.bot.paused:
            return

        if isinstance(msg, bytes):
            return

        try:
            raw_data = json.loads(msg)
        except:
            return

        if raw_data.get("t") != "MESSAGE_CREATE":
            return

        data = raw_data.get("d", {})
        if str(data.get("author", {}).get("id")) != self.bot.owo_bot_id:
            return

        components = parse_v2_message(data)
        if not components:
            return

        content = (data.get("content") or "").lower()
        v2_text = " ".join([c.content for c in components if c.name == "text_display"]).lower()
        full_text = f"{content} {v2_text}"
        
        is_spawn = "runs away" in full_text or "guild boss" in full_text
        fight_btn = next((c for c in components if c.custom_id == "guildboss_fight"), None)
        
        if not is_spawn and not fight_btn:
            if "already joined" in v2_text:
                pass 
            return

        channel_id = int(data.get("channel_id"))
        guild_id = str(data.get("guild_id") or "")


        if guild_id in [str(g) for g in self.ignore_guilds]:
            return
        can_join = False
        if self.join_all:
            can_join = True
        else:
            configured_channels = [str(c) for c in self.bot.channels]
            if str(channel_id) in configured_channels or str(channel_id) == str(self.bot.channel_id):
                can_join = True
            elif guild_id in self.playing_guild_ids:
                can_join = True
                self.bot.log("BOSS", f"Server-wide detected: Boss in non-playing channel ({channel_id}) of playing guild ({guild_id}).")

        if not can_join:
            return

        if not fight_btn:
            return

        battle_id = get_boss_battle_id(components)
        if battle_id and battle_id in self.joined_ids:
            return

        tracking_id = battle_id or f"msg_{data.get('id')}"

        self._check_reset()
        if self.tickets <= 0:
            return

        if random.randint(1, 100) > self.join_chance:
            self.bot.log("BOSS", "Boss spawned, but skipping due to join_chance.")
            self.joined_ids.add(tracking_id)
            return

        self.bot.log("BOSS", f"Boss Battle detected (ID: {tracking_id})! Attempting join...")
        
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        if self.bot.paused:
            return

        guild_id = data.get("guild_id")
        
        success = await self.bot.interactions.click_button_raw(
            custom_id=fight_btn.custom_id,
            message_id=data.get("id"),
            channel_id=channel_id,
            author_id=data.get("author", {}).get("id"),
            guild_id=guild_id,
            flags=data.get("flags", 0)
        )

        if success:
            self.tickets = max(0, self.tickets - 1)
            if tracking_id: self.joined_ids.add(tracking_id)
            self._save_state()
            self.bot.log("SUCCESS", f"Joined Boss Battle! Tickets remaining: {self.tickets}")
        else:
            self.bot.log("ERROR", "Failed to join Boss Battle.")

async def setup(bot):
    await bot.add_cog(Boss(bot))

