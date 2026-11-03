# This file is part of YuleeSelf-UwU.
# Copyright (c) 2025-Present Routo
#
# YuleeSelf-UwU is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with YuleeSelf-UwU. If not, see <https://www.gnu.org/licenses/>.


"""
Author: Routo
YuleeSelf-UwU - https://github.com/itsyulee/yulee-self
"""



import discord
from discord.ext import commands
import asyncio
import time
import re
import os
import core.state as state

class HuntBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active = True
        self.last_check = 0.0
        self.check_interval = 900
        self.pending_retry_delay = 60
        self.task = None
        self.password_reset_regex = r"(?<=Password will reset in )(\d+)"
        self.huntbot_time_regex = r"(\d+)([DHM])"
        self.last_upgrade_essence = 0
        self.last_upgrade_time = 0.0
        self.last_command_time = 0.0
        self.awaiting_password = False

    def trigger_action(self):
        cfg = self.bot.config.get('commands', {}).get('huntbot', {})
        amount = cfg.get('cash_to_spend', 16000)
        
        self.awaiting_password = True
        if 'huntbot' in self.bot.cmd_states:
            self.bot.cmd_states['huntbot']['content'] = f"huntbot {amount}"
            # Keep a short retry delay until OwO actually confirms hunt duration or password state
            self.bot.cmd_states['huntbot']['delay'] = self.pending_retry_delay
        
        self.last_command_time = time.time()
        self.last_check = time.time()
        self.bot.is_busy = True

    async def register_actions(self):
        cfg = self.bot.config.get('commands', {}).get('huntbot', {})
        if cfg.get('enabled', False):
            amount = cfg.get('cash_to_spend', 16000)
            self.bot.log("SYS", "HuntBot Module configured.")
            await self.bot.yulee_register_command(
                "huntbot",
                f"huntbot {amount}",
                priority=self.bot.get_cmd_priority("huntbot", 4),
                delay=self.check_interval,
                initial_offset=20
            )

    @commands.Cog.listener()
    async def on_message(self, message):
        await self._process_message(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        await self._process_message(after)

    async def _process_message(self, message):
        if message.channel.id != self.bot.channel_id:
            return

        # Learn our own guild nickname/display name and record exact timestamp when we send a command
        if self.bot.user and message.author.id == self.bot.user.id:
            if hasattr(self.bot, 'identity') and hasattr(self.bot.identity, 'learn_author_identity'):
                self.bot.identity.learn_author_identity(message.author)
            own_content = (message.content or "").lower().strip()
            prefix = self.bot.prefix.lower().strip()
            if own_content.startswith(prefix):
                cmd_body = own_content[len(prefix):].strip()
                if cmd_body.startswith(("hb", "huntbot", "autohunt")):
                    self.last_command_time = time.time()
            return

        monitor_id = str(self.bot.config.get('core', {}).get('monitor_bot_id', '408785106942164992'))
        if str(message.author.id) != monitor_id:
            return

        if self.bot.owo_user is None:
            self.bot.owo_user = message.author
        
        cfg = self.bot.config.get('commands', {}).get('huntbot', {})
        
        content = message.content or ""
        if message.embeds:
            content += " " + self.bot.get_full_content(message)
        content_lower = content.lower()
        
        # Strict per-account check: never override is_for_me with time-based guessing,
        # otherwise multiple accounts in the same channel will react to each other's password/timers!
        is_for_me = self.bot.is_message_for_me(message)
        if not is_for_me:
            return

        if "successfully upgraded" in content_lower and "animal essence" in content_lower:
            amt_match = re.search(r"with\s+\*\*?([\d,]+)\*\*? Animal Essence", content, re.IGNORECASE)
            if amt_match:
                amt = int(amt_match.group(1).replace(",", ""))
                self.bot.log("SUCCESS", f"HuntBot: Upgrade confirmed for {amt:,} essence.")
                self.last_upgrade_essence = amt
                self.last_upgrade_time = time.time()
            return

        if cfg.get('upgrade', {}).get('enabled', False) and message.embeds:
            for embed in message.embeds:
                if not (embed.author and self.bot.is_message_for_me(message, role="header")):
                    continue
                if not embed.fields:
                    continue

                from modules.nhuntbot_manager import manager

                essence = 0
                levels = {}
                invested = {}
                enabled = []

                trait_keywords = {
                    "efficiency": "efficiency",
                    "duration": "duration",
                    "cost": "cost",
                    "gain": "gain",
                    "exp": "experience",
                    "radar": "radar",
                }

                for field in embed.fields:
                    fname = field.name.lower() if field.name else ""
                    fval  = field.value  if field.value else ""

                    if "animal essence" in fname:
                        ess_match = re.search(r"`([\d,]+)`", field.name)
                        if ess_match:
                            essence = int(ess_match.group(1).replace(",", ""))
                        else:
                            ess_match2 = re.search(r"[\d,]+", field.name)
                            if ess_match2:
                                essence = int(ess_match2.group(0).replace(",", ""))
                        continue

                    for trait, keyword in trait_keywords.items():
                        if keyword in fname:
                            if "[MAX]" in fval:
                                levels[trait] = 1000
                                invested[trait] = 0
                                enabled.append(trait)
                            else:
                                lvl_match = re.search(r"Lvl (\d+) \[(\d+)/\d+\]", fval)
                                if lvl_match:
                                    levels[trait] = int(lvl_match.group(1))
                                    invested[trait] = int(lvl_match.group(2))
                                    enabled.append(trait)
                            break

                if enabled and essence > 0:
                    if essence == self.last_upgrade_essence and (time.time() - self.last_upgrade_time < 30):
                        return

                    alloc_cfg = cfg.get('upgrade', {})
                    allocations = manager.allocate(essence, levels, invested, enabled, alloc_cfg)
                    
                    if allocations:
                        self.last_upgrade_essence = essence
                        self.last_upgrade_time = time.time()
                        for trait, amount in allocations.items():
                            await self.bot.yulee_enqueue(f"upgrade {trait} {amount}", priority=2)
                            self.bot.log("SUCCESS", f"HuntBot: Enqueued upgrade for {trait.capitalize()} ({amount:,} essence).")
                elif enabled and essence == 0:
                    self.bot.log("AutoHunt", "HuntBot: No essence available — skipping upgrade.")
                elif essence > 0 and not enabled:
                    self.bot.log("AutoHunt", f"HuntBot: Essence={essence} but no traits parsed from fields.")
                break  

        if "i will be back in" in content_lower:
            total_seconds = 0
            found = False
            for amount, unit in re.findall(self.huntbot_time_regex, content.upper()):
                found = True
                if unit == "M": total_seconds += int(amount) * 60
                elif unit == "H": total_seconds += int(amount) * 3600
                elif unit == "D": total_seconds += int(amount) * 86400
            
            if found:
                self.awaiting_password = False
                self.check_interval = total_seconds + 30
                self.last_check = time.time()
                if 'huntbot' in self.bot.cmd_states:
                    self.bot.cmd_states['huntbot']['delay'] = self.check_interval
                    self.bot.cmd_states['huntbot']['last_ran'] = time.time()
                self.bot.is_busy = False
                self.bot.log("AutoHunt", f"HuntBot active. Next check in {round(total_seconds/60)}m")

        elif "i am back with" in content_lower or "beep boop. i am back with" in content_lower:
            rewards = content.split('back with')[-1].strip().upper() if 'back with' in content_lower else "UNKNOWN REWARDS"
            self.bot.log("AutoHunt", f"HuntBot returned! Rewards: {rewards[:100]}")
            self.awaiting_password = False
            self.check_interval = 900
            self.last_check = time.time() - 20
            if 'huntbot' in self.bot.cmd_states:
                self.bot.cmd_states['huntbot']['delay'] = 20
                self.bot.cmd_states['huntbot']['last_ran'] = time.time()
            self.bot.is_busy = False

        elif "please include your password" in content_lower:
            reset_match = re.search(self.password_reset_regex, content)
            minutes = int(reset_match.group(1)) if reset_match else 10
            wait_s = minutes * 60
            self.bot.log("AutoHunt", f"HuntBot stuck (password required). Reset in {minutes}m.")
            self.awaiting_password = False
            self.check_interval = wait_s + 30
            self.last_check = time.time()
            if 'huntbot' in self.bot.cmd_states:
                self.bot.cmd_states['huntbot']['delay'] = self.check_interval
                self.bot.cmd_states['huntbot']['last_ran'] = time.time()
            self.bot.is_busy = False

        elif "here is your password" in content_lower or "confirm your identity" in content_lower or "link below" in content_lower:
            self.bot.is_busy = True
            self.awaiting_password = True
            if 'huntbot' in self.bot.cmd_states:
                self.bot.cmd_states['huntbot']['delay'] = self.pending_retry_delay
                self.bot.cmd_states['huntbot']['last_ran'] = time.time()

            img_url = None
            if message.attachments:
                img_url = message.attachments[0].url
            elif message.embeds:
                for em in message.embeds:
                    if em.image:
                        img_url = em.image.url
                        break
            try:
                import modules.nhuntbotsolver as solver
                cash = cfg.get('cash_to_spend', 16000)
                if self.bot.session and img_url:
                    self.bot.log("AutoHunt", "Attempting YULEESELF Solver auto-solve...")
                    answer = await solver.solveHbCaptcha(img_url, self.bot.session)
                    
                    if answer and len(answer) > 0:
                        self.bot.log("SUCCESS", f"Captcha Solved: {answer}")
                        self.last_command_time = time.time()
                        await self.bot.yulee_enqueue(f"huntbot {cash} {answer}", priority=1)
                        
                        uid = str(self.bot.user.id)
                        if uid in state.account_stats:
                            self.bot.stats['captchas_solved_today'] = self.bot.stats.get('captchas_solved_today', 0) + 1
                            self.bot.stats['captcha_success_count'] = self.bot.stats.get('captcha_success_count', 0) + 1
                        self.bot.is_busy = False
                    else:
                        self.bot.log("WARN", "Could not solve captcha automatically. Waiting for manual solve or reset.")
                        self.bot.stats['current_captcha'] = {
                            'image_url': img_url,
                            'cash': cash,
                            'command_template': f"huntbot {cash} {{password}}",
                            'timestamp': time.time()
                        }
                        self.check_interval = 630
                        if 'huntbot' in self.bot.cmd_states:
                            self.bot.cmd_states['huntbot']['delay'] = self.check_interval
                            self.bot.cmd_states['huntbot']['last_ran'] = time.time()
                        self.bot.is_busy = False
            except Exception as e:
                self.bot.log("ERROR", f"Solver failed: {e}")
                self.bot.is_busy = False

        elif "wrong password" in content_lower or "incorrect password" in content_lower:
            self.bot.log("AutoHunt", "Wrong password provided. Waiting for reset.")
            self.awaiting_password = False
            self.check_interval = 630
            self.last_check = time.time()
            if 'huntbot' in self.bot.cmd_states:
                self.bot.cmd_states['huntbot']['delay'] = self.check_interval
                self.bot.cmd_states['huntbot']['last_ran'] = time.time()
            self.bot.is_busy = False


async def setup(bot):
    cog = HuntBot(bot)
    await bot.add_cog(cog)