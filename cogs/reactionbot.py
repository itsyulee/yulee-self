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
import random
import time
import datetime

class ReactionBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reaction_bot_id = 519287796549156864
        
    async def register_actions(self):
        self.bot.log("SYS", "ReactionBot settings refreshed (Live Sync).")
        
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id != self.reaction_bot_id:
            return
            
        rb_settings = self.bot.config.get("reactionBot", {})
        if not rb_settings.get("enabled", False):
            return
            
        all_channels = [str(c) for c in self.bot.channels]
        if str(message.channel.id) not in all_channels:
            return
            
        content = message.content
        if f"<@{self.bot.user.id}>" not in content and self.bot.user.name not in content:
            return
            
        hunt_battle = rb_settings.get("hunt_and_battle", False)
        owo = rb_settings.get("owo", False)
        pray_curse = rb_settings.get("pray_and_curse", False)
        delay_range = rb_settings.get("cooldown", [0.5, 1.0])
        
        trigger_delay = random.uniform(delay_range[0], delay_range[1])
        
        def force_run(cmd_id):
            if cmd_id in self.bot.cmd_states:
                now = time.time()
                last_sent = getattr(self.bot, "last_sent_time", 0)
                last_cmd = getattr(self.bot, "last_sent_command", "").lower()
                if now - last_sent < 5.0 and cmd_id in last_cmd:
                    return

                self.bot.cmd_states[cmd_id]["last_ran"] = 0
                self.bot.log("SYS", f"Reminder received for {cmd_id}! Forcing execution...")
        # forcerun logic
        if "**OwO**" in content and owo:
            self.bot.loop.call_later(trigger_delay, force_run, "owo")
            
        elif "**hunt/battle**" in content and hunt_battle:
            self.bot.loop.call_later(trigger_delay, force_run, "hunt")
            self.bot.loop.call_later(trigger_delay + 1, force_run, "battle")
            
        elif "**pray/curse**" in content and pray_curse:
            pray_cfg = self.bot.config.get("commands", {}).get("pray", {})
            curse_cfg = self.bot.config.get("commands", {}).get("curse", {})
            
            cmds = []
            if pray_cfg.get("enabled", False): cmds.append("pray")
            if curse_cfg.get("enabled", False): cmds.append("curse")
            
            if cmds:
                self.bot.loop.call_later(trigger_delay, force_run, random.choice(cmds))

async def setup(bot):
    await bot.add_cog(ReactionBot(bot))
