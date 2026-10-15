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
from discord.ext import commands

class SellSac(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_sell_time: float = 0.0
        self.last_sac_time: float = 0.0
        self.task: asyncio.Task | None = None

    async def cog_load(self):
        self.task = asyncio.create_task(self.main_loop())

    async def cog_unload(self):
        if self.task:
            self.task.cancel()

    async def main_loop(self):
        while True:
            try:
                cfg = self.bot.config.get('commands', {}).get('sell_sac', {})
                sell_cfg = cfg.get('sell', {})
                sac_cfg = cfg.get('sacrifice', {})
                
                autosell_enabled = sell_cfg.get('enabled', False)
                autosac_enabled = sac_cfg.get('enabled', False)

                if not autosell_enabled and not autosac_enabled:
                    await asyncio.sleep(60)
                    continue

                now = time.time()
                
                if autosell_enabled:
                    sell_interval = sell_cfg.get('interval_min', 20) * 60
                    if now - self.last_sell_time > sell_interval:
                        await self.bot.neura_enqueue(f"sell {sell_cfg.get('type', 'all')}", priority=4)
                        self.last_sell_time = now
                        self.bot.log("SYS", "Periodic AutoSell triggered.")

                if autosac_enabled:
                    sac_interval = sac_cfg.get('interval_min', 60) * 60
                    if now - self.last_sac_time > sac_interval:
                        cmd = "sc" if sac_cfg.get('use_shortform', False) else "sacrifice"
                        await self.bot.neura_enqueue(f"{cmd} {sac_cfg.get('type', 'all')}", priority=4)
                        self.last_sac_time = now
                        self.bot.log("SYS", "Periodic AutoSacrifice triggered.")

                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.bot.log("ERROR", f"SellSac loop error: {e}")
                await asyncio.sleep(60)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id != 408785106942164992 or not self.bot.is_message_for_me(message):
            return
        
        if str(message.channel.id) not in [str(c) for c in self.bot.channels]:
            return

        content = message.content.lower()
        if "you don't have enough cowoncy" in content or "you do not have enough cowoncy" in content:
            cfg = self.bot.config.get('commands', {}).get('sell_sac', {})
            sell_cfg = cfg.get('sell', {})
            if sell_cfg.get('enabled', False):
                await asyncio.sleep(2)
                await self.bot.neura_enqueue(f"sell {sell_cfg.get('type', 'all')}", priority=2)
                self.last_sell_time = time.time()
                self.bot.log("SYS", "Low funds detected. Triggered AutoSell.")

async def setup(bot):
    await bot.add_cog(SellSac(bot))
