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
import re
import time
import core.state as state
from discord.ext import commands

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active = True
        self.cash_regex = r"for \*\*(\d+)\*\* <:cowoncy:\d+>"
        self.cash_required = {
            1: 10, 2: 100, 3: 1000, 4: 10000, 
            5: 100000, 6: 1000000, 7: 10000000
        }
        self._pending_cash_check = False

    async def _send_buy_command(self):
        cnf = self.bot.config.get('commands', {}).get('shop', {})
        if not cnf.get('enabled', False):
            return

        items = cnf.get('itemsToBuy', [])
        if isinstance(items, int):
            items = [items]
        valid_items = [item for item in items if item in range(1, 8)]
        if not valid_items:
            return

        st = state.account_stats.get(self.bot.user_id, {})
        current_balance = st.get('current_cash')

        if current_balance is None:
            if not self._pending_cash_check:
                self.bot.log("Shop", "Balance unknown. Syncing via 'owo cash'...")
                self._pending_cash_check = True
                await self.bot.neura_enqueue("owo cash", priority=3)
            return

        self._pending_cash_check = False
        item_id = random.choice(valid_items)
        price = self.cash_required.get(item_id, 0)
        
        if current_balance >= price:
            await self.bot.neura_enqueue(f"owo buy {item_id}", priority=3)
            self.bot.log("Shop", f"Buying item #{item_id} (price: {price}, balance: {current_balance})")
        else:
            self.bot.log("Shop", f"Not enough cowoncy to buy item #{item_id} (need {price}, have {current_balance})")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id != 408785106942164992:
            return
            
        all_channels = [str(c) for c in self.bot.channels]
        if str(message.channel.id) not in all_channels:
            return

        if not self.bot.is_message_for_me(message):
            return

        content = message.content.lower()

        if "you currently have" in content and "cowoncy" in content:
            try:
                cash_match = re.search(r'you currently have[^\d]*([\d,]+)', message.content, re.IGNORECASE)
                if cash_match:
                    cash_str = cash_match.group(1).replace(',', '')
                    st = state.account_stats.get(self.bot.user_id, {})
                    st['current_cash'] = int(cash_str)
                    st['last_cash_update'] = time.time()
                    state.save_account_stats()
                    self.bot.log("Shop", f"Balance synced: {cash_str} cowoncy")
                    self._pending_cash_check = False
            except Exception:
                pass

        if "you bought a" in content:
            match = re.search(self.cash_regex, message.content)
            if match:
                price = int(match.group(1))
                st = state.account_stats.get(self.bot.user_id, {})
                if 'current_cash' in st and st['current_cash'] is not None:
                    st['current_cash'] -= price
                    state.save_account_stats()
                    self.bot.log("SUCCESS", f"Shop: Bought item. Balance updated: -{price} cowoncy")

    async def _sync_balance(self):
        """Periodically send 'owo cash' to keep the balance up to date."""
        cnf = self.bot.config.get('commands', {}).get('shop', {})
        if not cnf.get('enabled', False):
            return
        self.bot.log("Shop", "Auto-syncing balance via 'owo cash'...")
        await self.bot.neura_enqueue("owo cash", priority=3)

    async def register_actions(self):
        cnf = self.bot.config.get('commands', {}).get('shop', {})
        if cnf.get('enabled', False):
            cooldown = cnf.get('cooldown', 3600)
            await self.bot.neura_register_command(
                "shop_buy", 
                self._send_buy_command, 
                priority=self.bot.get_cmd_priority("shop_buy", 3), 
                delay=cooldown, 
                initial_offset=random.randint(60, 120)
            )

            await self.bot.neura_register_command(
                "shop_cash_sync",
                self._sync_balance,
                priority=self.bot.get_cmd_priority("shop_cash_sync", 3),
                delay=7200,
                initial_offset=30
            )

async def setup(bot):
    cog = Shop(bot)
    await bot.add_cog(cog)
