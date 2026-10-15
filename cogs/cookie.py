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



from discord.ext import commands
import asyncio
import time
import json
import random
import os
import re

class Cookie(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active = True
        self.stats_file = 'data/stats_cookie.json'
        self.last_run = self._load_last_run()
        self.last_cookie_sent = 0

    def _load_last_run(self):
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    data = json.load(f)
                    return data.get(str(self.bot.user_id), 0)
            except:
                return 0
        return 0

    def _save_last_run(self, timestamp):
        data = {}
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    data = json.load(f)
            except:
                pass
        data[str(self.bot.user_id)] = timestamp
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(data, f, indent=4)
        except:
            pass

    def trigger_action(self):
        cfg = self.bot.config.get('commands', {}).get('cookie', {})
        user_to_cookie = cfg.get('id')
        if user_to_cookie:
            self.bot.log("INFO", f"Sending cookie command to {user_to_cookie}...")
            cmd = f"cookie {user_to_cookie}"
            self.bot.cmd_states['cookie']['content'] = cmd

            self.last_run = time.time()
            self.last_cookie_sent = time.time()
            self.cooldown_until = self.last_run + 86400
            self._save_last_run(self.last_run)
            self.bot.cmd_states['cookie']['delay'] = 86400

    @commands.Cog.listener()
    async def on_message(self, message):
        await self._process_response(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        await self._process_response(after)

    async def _process_response(self, message):
        core_config = self.bot.config.get('core', {})
        monitor_id = str(core_config.get('monitor_bot_id', '408785106942164992'))
        if str(message.author.id) != monitor_id: return
        if self.bot.owo_user is None:
            self.bot.owo_user = message.author
        all_channels = [str(c) for c in self.bot.channels]
        if str(message.channel.id) not in all_channels:
            return
        
        full_content = self.bot.get_full_content(message)
        
        if not self.bot.is_message_for_me(message): return
        
        if "wait" in full_content:
            time_since_last = time.time() - self.last_cookie_sent
            if time_since_last < 20.0 or "cookie" in full_content:
                self._sync_cooldown(full_content)
                self.last_cookie_sent = 0
            return
            
        is_sender = self.bot.is_message_for_me(message, role="target", keyword="got a cookie from") or \
                    self.bot.is_message_for_me(message, role="source", keyword="sent a cookie to")
        
        if not is_sender: return
        
        if "sent a cookie to" in full_content or "got a cookie from" in full_content:
            self.last_run = time.time()
            self._save_last_run(self.last_run)
            self.cooldown_until = self.last_run + 86400  
            self.bot.log("SUCCESS", "Cookie successfully sent.")

    def _sync_cooldown(self, message):
        h_match = re.search(r'(\d+)\s*[hH]', message)
        m_match = re.search(r'(\d+)\s*[mM]', message)
        s_match = re.search(r'(\d+)\s*[sS]', message)
        
        h = int(h_match.group(1)) if h_match else 0
        m = int(m_match.group(1)) if m_match else 0
        s = int(s_match.group(1)) if s_match else 0
        total_seconds = (h * 3600) + (m * 60) + s
        
        if total_seconds > 0:
            self.bot.log("COOLDOWN", f"Cookie cooldown synced: {h}h {m}m {s}s remaining.")
            self.cooldown_until = time.time() + total_seconds + random.randint(10, 30)
            self.last_run = time.time() - (86400 - (total_seconds + 30))
            self._save_last_run(self.last_run)
            
            if 'cookie' in self.bot.cmd_states:
                self.bot.cmd_states['cookie']['delay'] = total_seconds + random.randint(10, 30)
                self.bot.cmd_states['cookie']['last_ran'] = time.time()

    async def register_actions(self):
        cfg = self.bot.config.get('commands', {}).get('cookie', {})
        if cfg.get('enabled', False):
            user_to_cookie = cfg.get('id')
            if user_to_cookie:
                last_run = self._load_last_run()
                remaining = last_run + 86400 - time.time()
                
                if remaining <= 0:
                    delay = 5 
                else:
                    delay = remaining
                    h = int(delay // 3600)
                    m = int((delay % 3600) // 60)
                    self.bot.log("INFO", f"Cookie on cooldown: {h}h {m}m remaining.")
                
                cmd = f"cookie {user_to_cookie}"
                await self.bot.neura_register_command("cookie", cmd, priority=self.bot.get_cmd_priority("cookie", 4), delay=max(10, delay), initial_offset=0)

async def setup(bot):
    cog = Cookie(bot)
    await bot.add_cog(cog)
