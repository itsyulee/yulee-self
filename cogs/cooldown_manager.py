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
import re
import time
import core.state as state

class CooldownManager:
    def __init__(self, bot):
        self.bot = bot
        
    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            content = message.content.lower().strip()
            prefix = self.bot.prefix.lower().strip()
            
            if content.startswith(prefix):
                remaining = content[len(prefix):].strip()
                parts = remaining.split()
                
                if not parts:
                    cmd_part = "owo" 
                else:
                    cmd_part = parts[0]

                alias_map = {
                    "h": "hunt",
                    "b": "battle",
                    "curse": "cursepray",
                    "pray": "cursepray",
                    "owo": "owo"
                }
                cmd_id = alias_map.get(cmd_part, cmd_part)

                if cmd_id in self.bot.cmd_states:
                    self.bot.cmd_states[cmd_id]['last_ran'] = time.time()

                    is_echo = (content == self.bot.last_sent_command.lower().strip() and 
                              time.time() - self.bot.last_sent_time < 1.2)
                    
                    if not is_echo:
                        silent_cmds = ['hunt', 'battle', 'owo']
                        if cmd_id not in silent_cmds:
                            self.bot.log("SYS", f"Manual command sync: {cmd_id}")
                
                self.last_manual_cmd = cmd_id
                self.last_manual_time = time.time()
            return

        monitor_id = str(self.bot.config.get('core', {}).get('monitor_bot_id', '408785106942164992'))
        if str(message.author.id) != monitor_id:
            return
            
        if message.channel.id != self.bot.channel_id:
            return
        
        content = message.content.lower()
        is_for_me = self.bot.is_message_for_me(message)
        if not is_for_me:
            return


        if "slow down" in content or "try the command again" in content:
            wait_seconds = 0
            
            ts_match = re.search(r'<t:(\d+):r>', content)
            if ts_match:
                target_ts = int(ts_match.group(1))
                wait_seconds = max(0, target_ts - int(time.time()))
                self.bot.log("COOLDOWN", f"Syncing via Timestamp: {wait_seconds}s")

            else:
                sec_match = re.search(r'(\d+)\s*seconds?', content)
                if sec_match:
                    wait_seconds = int(sec_match.group(1))
                    self.bot.log("COOLDOWN", f"Syncing via Seconds: {wait_seconds}s")
                else:
                    wait_seconds = 5
                    self.bot.log("COOLDOWN", f"Generic slow-down detected. Applying 5s safety pause.")

            if wait_seconds > 0:
                cmd_id = None
                if hasattr(self, 'last_manual_time') and time.time() - self.last_manual_time < 5:
                    cmd_id = self.last_manual_cmd
                else:
                    last_cmd = self.bot.last_sent_command.lower().strip()
                    prefix = self.bot.prefix.lower().strip()
                    if last_cmd.startswith(prefix):
                        cmd_part = last_cmd[len(prefix):].strip().split()[0]
                        alias_map = {
                            "h": "hunt", "b": "battle", 
                            "curse": "cursepray", "pray": "cursepray"
                        }
                        cmd_id = alias_map.get(cmd_part, cmd_part)

                if wait_seconds <= 15:
                    self.bot.throttle_until = time.time() + wait_seconds + 0.5
                else:
                    pass

                if cmd_id and cmd_id in self.bot.cmd_states:
                    delay = self.bot.cmd_states[cmd_id]['delay']
                    self.bot.cmd_states[cmd_id]['last_ran'] = time.time() - delay + wait_seconds + 1

                    if wait_seconds > 15:
                        self.bot.log("COOLDOWN", f"Synced {cmd_id} cooldown: {wait_seconds}s (Grinding continues)")
                    else:
                        silent_cmds = ['hunt', 'battle', 'owo']
                        if cmd_id not in silent_cmds:
                            self.bot.log("COOLDOWN", f"Refined {cmd_id} timer (Global Pause: {wait_seconds}s)")

        elif "too tired to run" in content:
            self.bot.log("COOLDOWN", "Too tired to run (Synced)")

async def setup(bot):
    cog = CooldownManager(bot)
    bot.add_listener(cog.on_message, 'on_message')