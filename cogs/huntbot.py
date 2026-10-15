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
import re
import os
import core.state as state

class HuntBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active = True
        self.last_check = 0.0
        self.check_interval = 900
        self.task = None
        self.password_reset_regex = r"(?<=Password will reset in )(\d+)"
        self.huntbot_time_regex = r"(\d+)([DHM])"
        self.last_upgrade_essence = 0
        self.last_upgrade_time = 0.0

    def trigger_action(self):
        cfg = self.bot.config.get('commands', {}).get('huntbot', {})
        amount = cfg.get('cash_to_spend', 16000)
        
        if 'huntbot' in self.bot.cmd_states:
            self.bot.cmd_states['huntbot']['content'] = f"huntbot {amount}"
            self.bot.cmd_states['huntbot']['delay'] = self.check_interval
        
        self.last_command_time = time.time()
        self.last_check = time.time()
        self.bot.is_busy = True

    async def register_actions(self):
        cfg = self.bot.config.get('commands', {}).get('huntbot', {})
        if cfg.get('enabled', False):
            self.bot.log("SYS", "HuntBot Module configured.")
            await self.bot.neura_register_command("huntbot", "huntbot 16000", priority=self.bot.get_cmd_priority("huntbot", 4), delay=900, initial_offset=20)
            self.trigger_action()

    @commands.Cog.listener()
    async def on_message(self, message):
        await self._process_message(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        await self._process_message(after)

    async def _process_message(self, message):
        if self.bot.owo_user is None:
            self.bot.owo_user = message.author
        if message.channel.id != self.bot.channel_id: return
        
        cfg = self.bot.config.get('commands', {}).get('huntbot', {})
        
        content = message.content or ""
        if message.embeds:
            content += " " + self.bot.get_full_content(message)
        content_lower = content.lower()
        
        is_for_me = self.bot.is_message_for_me(message)
        
        generic_huntbot_patterns = ["i will be back in", "i am back with", "beep boop. i am back with"]
        if not is_for_me and any(p in content_lower for p in generic_huntbot_patterns):
            if hasattr(self, 'last_command_time') and (time.time() - self.last_command_time < 45):
                is_for_me = True

        if not is_for_me:
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
                            await self.bot.neura_enqueue(f"upgrade {trait} {amount}", priority=2)
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
                self.check_interval = total_seconds + 30
                self.last_check = time.time()
                if 'huntbot' in self.bot.cmd_states:
                    self.bot.cmd_states['huntbot']['delay'] = self.check_interval
                    self.bot.cmd_states['huntbot']['last_ran'] = time.time()
                self.bot.is_busy = False
                self.bot.log("AutoHunt", f"HuntBot busy. Resyncing for {round(total_seconds/60)}m")

        elif "i am back with" in content_lower or "beep boop. i am back with" in content_lower:
            rewards = content.split('back with')[-1].strip().upper() if 'back with' in content_lower else "UNKNOWN REWARDS"
            self.bot.log("AutoHunt", f"HuntBot returned! Rewards: {rewards[:100]}")
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
            self.check_interval = wait_s + 30
            self.last_check = time.time()
            if 'huntbot' in self.bot.cmd_states:
                self.bot.cmd_states['huntbot']['delay'] = self.check_interval
                self.bot.cmd_states['huntbot']['last_ran'] = time.time()
            self.bot.is_busy = False

        elif "here is your password" in content_lower or "confirm your identity" in content_lower or "link below" in content_lower:
            self.bot.is_busy = True

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
                if self.bot.session and img_url:
                    self.bot.log("AutoHunt", "Attempting NeuraSolver auto-solve...")
                    answer = await solver.solveHbCaptcha(img_url, self.bot.session)
                    
                    if answer and len(answer) > 0:
                        self.bot.log("SUCCESS", f"Captcha Solved: {answer}")
                        cash = cfg.get('cash_to_spend', 15000)
                        await self.bot.neura_enqueue(f"autohunt {cash} {answer}", priority=1)
                        
                        uid = str(self.bot.user.id)
                        if uid in state.account_stats:
                            self.bot.stats['captchas_solved_today'] = self.bot.stats.get('captchas_solved_today', 0) + 1
                            self.bot.stats['captcha_success_count'] = self.bot.stats.get('captcha_success_count', 0) + 1
                        self.bot.is_busy = False
                    else:
                        self.bot.log("WARN", "Could not solve captcha automatically.")
                        # base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        # path = os.path.join(base, "beeps", "huntbot_image_beep.mp3")
                        # plat_settings = self.bot.config.get('platform_settings', {})
                        # if plat_settings.get('desktop_notifications', True):
                        #     if os.path.exists(path):
                        #         asyncio.create_task(self._play_beep_async(path))
            except Exception as e:
                self.bot.log("ERROR", f"Solver failed: {e}")
                # base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                # path = os.path.join(base, "beeps", "huntbot_image_beep.mp3")
                # if os.path.exists(path):
                #     asyncio.create_task(self._play_beep_async(path))

        elif "wrong password" in content_lower or "incorrect password" in content_lower:
            self.bot.log("AutoHunt", "Wrong password provided. Waiting for reset.")
            self.check_interval = 630
            self.last_check = time.time()
            if 'huntbot' in self.bot.cmd_states:
                self.bot.cmd_states['huntbot']['delay'] = self.check_interval
                self.bot.cmd_states['huntbot']['last_ran'] = time.time()
            self.bot.is_busy = False


    # async def _play_beep_async(self, path):
    #     if not os.path.exists(path): return

    #     if hasattr(self.bot, 'is_mobile') and self.bot.is_mobile:
    #         try:
    #             os.system(f'termux-media-player play "{path}"')
    #         except:
    #             pass
    #         return

    #     try:
    #         from playsound3 import playsound
    #         loop = asyncio.get_event_loop()
    #         await loop.run_in_executor(None, lambda: playsound(path, block=False))
    #     except:
    #         pass

async def setup(bot):
    cog = HuntBot(bot)
    await bot.add_cog(cog)
