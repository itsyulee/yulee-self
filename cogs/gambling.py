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
import random
import re
import core.state as state
from discord.ext import commands

class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active = True
        self.task = None
        self.martingale_states = {}
        self.last_outcomes = {}
        self.gambling_stats = {}

    def _get_gambling_cfg(self):
        return self.bot.config.get('gambling', {})

    def _get_cmd_cfg(self, cmd):
        return self.bot.config.get('commands', {}).get(cmd, {})

    def _get_current_cash(self):
        uid = str(self.bot.user.id) if (hasattr(self.bot, '_connection') and self.bot.user) else str(getattr(self.bot, 'user_id', ''))
        st = state.account_stats.get(uid, {})
        return st.get('current_cash', None)

    def _check_safeguards(self):
        gamble_cfg = self._get_gambling_cfg()
        min_balance = gamble_cfg.get('min_balance', 0)
        max_balance = gamble_cfg.get('max_balance', 999999999)
        current_cash = self._get_current_cash()
        if current_cash is None:
            self.bot.log("GAMBLING", "Cash unknown. Skipping bet until balance sync.")
            return False
        if current_cash < min_balance:
            self.bot.log("GAMBLING", f"Stop-loss: {current_cash} < min {min_balance}. Suspending.")
            return False
        if current_cash > max_balance:
            self.bot.log("GAMBLING", f"Take-profit: {current_cash} > max {max_balance}. Suspending.")
            return False
        return True

    def _parse_blackjack_outcome(self, embed):
        footer = embed.footer.text if embed.footer else ""
        if "You won" in footer:
            return "win"
        if "You lost" in footer:
            return "loss"
        if "You tied" in footer or "You both bust" in footer:
            return "tie"
        return None

    def _get_bet_amount(self, cmd, base_amount):
        gamble_cfg = self._get_gambling_cfg()
        strategy = gamble_cfg.get('bet_strategy', 'flat')
        max_bet = gamble_cfg.get('max_bet', 100000)

        if strategy == 'martingale':
            if cmd not in self.martingale_states:
                self.martingale_states[cmd] = {
                    'current_bet': base_amount,
                    'base_bet': base_amount,
                    'consecutive_losses': 0,
                    'consecutive_wins': 0
                }
            bet = self.martingale_states[cmd]['current_bet']
            return min(bet, max_bet)
        else:
            return min(base_amount, max_bet)

    def _update_martingale(self, cmd, won):
        if cmd not in self.martingale_states:
            return
        m_state = self.martingale_states[cmd]
        base = m_state['base_bet']
        max_bet = self._get_gambling_cfg().get('max_bet', 100000)
        if won:
            m_state['current_bet'] = base
            m_state['consecutive_losses'] = 0
            m_state['consecutive_wins'] += 1
            self.bot.log("GAMBLING", f"Martingale: Won! Reset to {base}")
        else:
            m_state['consecutive_losses'] += 1
            m_state['consecutive_wins'] = 0
            m_state['current_bet'] = min(m_state['current_bet'] * 2, max_bet)
            self.bot.log("GAMBLING", f"Martingale: Lost! Next: {m_state['current_bet']}")

    def _record_outcome(self, cmd, won, amount):
        uid = str(self.bot.user.id) if (hasattr(self.bot, '_connection') and self.bot.user) else str(getattr(self.bot, 'user_id', ''))
        if uid not in self.gambling_stats:
            self.gambling_stats[uid] = {
                'total_wins': 0, 'total_losses': 0, 'total_wagered': 0,
                'net_profit': 0, 'current_streak': 0, 'best_streak': 0,
                'worst_streak': 0, 'biggest_win': 0, 'last_outcome': None
            }
        gs = self.gambling_stats[uid]
        gs['total_wagered'] += amount
        gs['last_outcome'] = 'win' if won else 'loss'
        if won:
            gs['total_wins'] += 1
            gs['net_profit'] += amount
            gs['current_streak'] = max(1, gs['current_streak'] + 1) if gs['current_streak'] >= 0 else 1
            gs['best_streak'] = max(gs['best_streak'], gs['current_streak'])
            gs['biggest_win'] = max(gs['biggest_win'], amount)
        else:
            gs['total_losses'] += 1
            gs['net_profit'] -= amount
            gs['current_streak'] = min(-1, gs['current_streak'] - 1) if gs['current_streak'] <= 0 else -1
            gs['worst_streak'] = min(gs['worst_streak'], gs['current_streak'])
        st = state.account_stats.get(uid, {})
        if st:
            st['gambling_stats'] = gs
            state.save_account_stats()

    def _get_current_bet_for_cmd(self, cmd):
        cmd_cfg = self._get_cmd_cfg(cmd)
        base_amount = cmd_cfg.get('amount', 1)
        return self._get_bet_amount(cmd, base_amount)

    def trigger_coinflip(self):
        if not self._check_safeguards():
            return
        cfg = self._get_cmd_cfg('coinflip')
        amount = self._get_current_bet_for_cmd('coinflip')
        side = cfg.get('side', 'h')
        self.bot.cmd_states['coinflip']['content'] = f"cf {side} {amount}"
        self.bot.cmd_states['coinflip']['delay'] = random.uniform(30, 60)
        self.bot.log("GAMBLING", f"Coinflip: Betting {amount} on {side}")

    def trigger_slots(self):
        if not self._check_safeguards():
            return
        cfg = self._get_cmd_cfg('slots')
        amount = self._get_current_bet_for_cmd('slots')
        self.bot.cmd_states['slots']['content'] = f"slots {amount}"
        self.bot.cmd_states['slots']['delay'] = random.uniform(25, 50)
        self.bot.log("GAMBLING", f"Slots: Betting {amount}")

    def trigger_blackjack(self):
        if not self._check_safeguards():
            return
        cfg = self._get_cmd_cfg('blackjack')
        amount = self._get_current_bet_for_cmd('blackjack')
        self.bot.cmd_states['blackjack']['content'] = f"bj {amount}"
        self.bot.cmd_states['blackjack']['delay'] = random.uniform(40, 70)
        self.bot.log("GAMBLING", f"Blackjack: Betting {amount}")

    async def register_actions(self):
        cfg_cf = self._get_cmd_cfg('coinflip')
        if cfg_cf.get('enabled', False):
            self.bot.log("SYS", "Gambling (Coinflip) Module configured.")
            await self.bot.neura_register_command("coinflip", "cf", priority=self.bot.get_cmd_priority("coinflip", 3), delay=random.uniform(30, 60), initial_offset=15)
            self.trigger_coinflip()
        cfg_slots = self._get_cmd_cfg('slots')
        if cfg_slots.get('enabled', False):
            self.bot.log("SYS", "Gambling (Slots) Module configured.")
            await self.bot.neura_register_command("slots", "slots", priority=self.bot.get_cmd_priority("slots", 3), delay=random.uniform(25, 50), initial_offset=20)
            self.trigger_slots()
        cfg_bj = self._get_cmd_cfg('blackjack')
        if cfg_bj.get('enabled', False):
            self.bot.log("SYS", "Gambling (Blackjack) Module configured.")
            await self.bot.neura_register_command("blackjack", "bj", priority=self.bot.get_cmd_priority("blackjack", 3), delay=random.uniform(40, 70), initial_offset=25)
            self.trigger_blackjack()

    @commands.Cog.listener()
    async def on_message(self, message):
        await self._process_response(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        await self._process_response(after)

    async def _process_response(self, message):
        core_config = self.bot.config.get('core', {})
        monitor_id = str(core_config.get('monitor_bot_id', '408785106942164992'))
        if str(message.author.id) != monitor_id:
            return
        if self.bot.owo_user is None:
            self.bot.owo_user = message.author
        all_channels = [str(c) for c in self.bot.channels]
        if str(message.channel.id) not in all_channels:
            return
        full_content = self.bot.get_full_content(message)
        is_for_me = self.bot.is_message_for_me(message)
        if not is_for_me:
            return
        content_lower = full_content.lower()

        if "chose heads" in content_lower or "chose tails" in content_lower:
            won = "won" in content_lower or "win" in content_lower
            self._handle_gamble_outcome('coinflip', won, content_lower)
        elif "___slots___" in content_lower or "slot" in content_lower:
            won = "won" in content_lower or "win" in content_lower
            self._handle_gamble_outcome('slots', won, content_lower)
        elif "blackjack" in content_lower or "bj" in content_lower:
            outcome = None
            if message.embeds:
                outcome = self._parse_blackjack_outcome(message.embeds[0])
            if outcome == "win":
                self._handle_gamble_outcome('blackjack', True, content_lower)
            elif outcome == "loss":
                self._handle_gamble_outcome('blackjack', False, content_lower)
            elif outcome == "tie":
                self._sync_cash_from_response(content_lower)
                self.bot.log("GAMBLING", "Blackjack: Tie/Bust - no win/loss recorded.")
            else:
                won = "won" in content_lower and "lost" not in content_lower
                if "won" in content_lower or "lost" in content_lower:
                    self._handle_gamble_outcome('blackjack', won, content_lower)
        elif any(phrase in content_lower for phrase in ["you won", "you lost", "bet"]):
            won = "won" in content_lower and "lost" not in content_lower
            for game_cmd in ['coinflip', 'slots', 'blackjack']:
                if self._is_recent_gamble(game_cmd):
                    self._handle_gamble_outcome(game_cmd, won, content_lower)
                    break

    def _is_recent_gamble(self, cmd):
        if cmd not in self.bot.cmd_states:
            return False
        elapsed = time.time() - self.bot.cmd_states[cmd].get('last_ran', 0)
        return elapsed < 30

    def _handle_gamble_outcome(self, cmd, won, content):
        cmd_cfg = self._get_cmd_cfg(cmd)
        base_amount = cmd_cfg.get('amount', 1)
        bet_amount = self._get_current_bet_for_cmd(cmd)

        self._update_martingale(cmd, won)

        self._record_outcome(cmd, won, bet_amount)

        if cmd == 'coinflip':
            side = cmd_cfg.get('side', 'h')
            next_bet = self._get_current_bet_for_cmd('coinflip')
            self.bot.cmd_states['coinflip']['content'] = f"cf {side} {next_bet}"
        elif cmd == 'slots':
            next_bet = self._get_current_bet_for_cmd('slots')
            self.bot.cmd_states['slots']['content'] = f"slots {next_bet}"

        self._sync_cash_from_response(content)
        outcome_str = "WON" if won else "LOST"
        uid = str(self.bot.user.id) if (hasattr(self.bot, '_connection') and self.bot.user) else str(getattr(self.bot, 'user_id', ''))
        gs = self.gambling_stats.get(uid, {})
        self.bot.log("GAMBLING", f"{cmd.upper()}: {outcome_str} (Bet: {bet_amount}, Net: {gs.get('net_profit', 0):,})")

    def _sync_cash_from_response(self, content):
        cash_match = re.search(r'(?:now have|balance[^\d]*)([,\d]+)', content, re.IGNORECASE)
        if not cash_match:
            cash_match = re.search(r'(?:won|lost)\s+([,\d]+)\s+cowoncy', content, re.IGNORECASE)
        if cash_match:
            try:
                cash_str = cash_match.group(1).replace(',', '')
                cash_val = int(cash_str)
                uid = str(self.bot.user.id) if (hasattr(self.bot, '_connection') and self.bot.user) else str(getattr(self.bot, 'user_id', ''))
                st = state.account_stats.get(uid, {})
                if st:
                    st['current_cash'] = cash_val
                    st['last_cash_update'] = time.time()
                    state.save_account_stats()
            except (ValueError, IndexError):
                pass

async def setup(bot):
    cog = Gambling(bot)
    await bot.add_cog(cog)