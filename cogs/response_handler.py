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
import re
import time
import random
import core.state as state
from utils import blackjack_agent

class ResponseHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_success_time = {}
        self.success_triggers = {
            'hunt': ['you found:', 'you found', 'found:', 'is empowered by', 'caught a', 'caught an'],
            'battle': ['you won', 'you lost', 'goes into battle', 'battle!', 'won in', 'lost in', 'team gained', 'streak:', 'battle team gained', 'battle goes into', 'you won in', 'you lost in', 'wins!'],
            'curse': ['puts a curse on', 'is cursed', 'ghostly curse'],
            'pray': ['prays for', 'prays...'],
            'cookie': ['gave a cookie to', 'sent a cookie', 'got a cookie from'],
            'daily': ['collected your daily', 'daily reward'],
            'emote': [' hugs ', ' kisses ', ' slaps ', ' punches ', ' cuddles ', ' pats ', ' pokes ', ' bites ', ' blushes at ', ' stares at ', ' cries to ', ' pouts at '],
            'gamble': ['chose heads', 'chose tails', '___slots___', 'bet <:cowoncy:']
        }

    @commands.Cog.listener()
    async def on_message(self, message):
        await self._process_response(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        await self._process_response(after)

    async def _process_response(self, message):
        if message.author.id == self.bot.user.id:
            content_clean = (message.content or "").lower().strip()
            prefix = self.bot.prefix.lower().strip()
            if content_clean in ["owo", "uwu"] or content_clean == f"{prefix}owo" or content_clean == f"{prefix}uwu":
                self._track_quest_progress("Say 'owo'")
            return

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

        await self._handle_blackjack(message)

        await self._handle_cooldowns(full_content, message)

        if "challenges you to a duel" in full_content and self.bot.user.mentioned_in(message):
            accepted_via_button = False
            if message.components:
                for row in message.components:
                    for comp in row.children:
                        if getattr(comp, 'custom_id', None) == 'battle_accept':
                            self.bot.log("INFO", "Accepting battle challenge via button click...")
                            accepted_via_button = await self.bot.interactions.click_button('battle_accept', message)
                            break
            if not accepted_via_button:
                self.bot.log("INFO", "Fallback: Accepting battle challenge via owo ab command...")
                await self.bot.neura_enqueue("owo ab", priority=4)

        await self._handle_battle_results(full_content, message)

        if self.bot.is_message_for_me(message) or any(t in full_content for t in self.success_triggers['emote']):
            xp_match = re.search(r'(?:\+|gained\s+)(\d+)\s*xp', full_content, re.IGNORECASE)
            if xp_match:
                xp_gained = int(xp_match.group(1))
                self._track_quest_progress("xp from", count=xp_gained)

            await self._handle_success(full_content, message)
            await self._handle_status_updates(full_content, message)

    def _track_quest_progress(self, desc_contains, count=1, exclude=None):
        quests = self.bot.stats.get('quest_data', [])
        updated = False
        for q in quests:
            if q.get('completed', False):
                continue
            q_desc = q.get('description', '').lower()
            if desc_contains.lower() in q_desc:
                if exclude and exclude.lower() in q_desc:
                    continue
                q['current'] = min(q['total'], q['current'] + count)
                if q['current'] >= q['total']:
                    q['completed'] = True
                    self.bot.log("SUCCESS", f"QUEST COMPLETED: {q['description']}")
                updated = True
        if updated:
            self.bot.stats['quest_data'] = quests

    async def _handle_success(self, content, message):
        now = time.time()
        for cmd_type, triggers in self.success_triggers.items():
            if cmd_type == 'battle':
                continue
            for trigger in triggers:
                if trigger in content:
                    if now - self.last_success_time.get(cmd_type, 0) < 5.0 and cmd_type != 'emote':
                        break
                    self.last_success_time[cmd_type] = now
                    if cmd_type == 'hunt':
                        self.bot.stats['hunt_count'] = self.bot.stats.get('hunt_count', 0) + 1
                        self.bot.log("SUCCESS", f"Hunt confirmed for {self.bot.display_name}")
                        self._track_quest_progress("Manually hunt")
                        for q in self.bot.stats.get('quest_data', []):
                            if q.get('completed', False):
                                continue
                            q_desc = q.get('description', '').lower()
                            if "hunt 3 animals that are" in q_desc:
                                match_rank = re.search(r'hunt 3 animals that are\s+(\w+)', q_desc)
                                if match_rank:
                                    target_rank = match_rank.group(1).lower()
                                    if target_rank in content or f":{target_rank}:" in content:
                                        self._track_quest_progress(q.get('description'), count=1)
                    elif cmd_type == 'curse':
                        if self.bot.is_message_for_me(message, role="target", keyword="puts a curse on"):
                            self._track_quest_progress("Have a friend curse you")
                            self.bot.log("SUCCESS", f"Friend Curse confirmed (received) for {self.bot.display_name}")
                    elif cmd_type == 'pray':
                        if self.bot.is_message_for_me(message, role="target", keyword="prays for"):
                            self._track_quest_progress("Have a friend pray to you")
                            self.bot.log("SUCCESS", f"Friend Pray confirmed (received) for {self.bot.display_name}")
                    elif cmd_type == 'cookie':
                        if self.bot.is_message_for_me(message, role="source", keyword="got a cookie from"):
                            self.bot.log("SUCCESS", f"Cookie received confirmed for {self.bot.display_name}")
                            self._track_quest_progress("Receive a cookie from")
                    elif cmd_type == 'emote':
                        if self.bot.is_message_for_me(message, role="source", keyword=trigger.strip()):
                            self._track_quest_progress("Use an action command on someone")
                        elif self.bot.is_message_for_me(message, role="target", keyword=trigger.strip()):
                            self._track_quest_progress("Have a friend use an action command on you")
                    elif cmd_type == 'gamble':
                        self.bot.log("SUCCESS", f"Gamble confirmed for {self.bot.display_name}")
                        self._track_quest_progress("Gamble")
                    break

    async def _handle_battle_results(self, content, message):
        is_battle_msg = any(trigger in content for trigger in ['goes into battle', 'battle!', 'won in', 'lost in', 'streak:', 'you won', 'you lost', 'wins!'])
        if not is_battle_msg:
            return
        is_for_me = self.bot.is_message_for_me(message)
        if is_for_me:
            now = time.time()
            if now - self.last_success_time.get('battle', 0) > 5.0:
                self.last_success_time['battle'] = now
                self.bot.stats['battle_count'] = self.bot.stats.get('battle_count', 0) + 1
                self.bot.log("SUCCESS", f"Battle confirmed for {self.bot.display_name}")
                if "wins!" in content:
                    self._track_quest_progress("battle with a friend")
                else:
                    self._track_quest_progress("Battle", exclude="friend")

    async def _handle_cooldowns(self, content, message):
        if "slow down~" in content or "too fast for me" in content:
            wait_time = random.uniform(3.0, 5.0)
            self.bot.throttle_until = time.time() + wait_time
            self.bot.log("COOLDOWN", f"Global Throttle: pausing {round(wait_time, 1)}s")

    async def _handle_status_updates(self, content, message):
        pass

    async def _handle_blackjack(self, message):
        if not message.embeds:
            return

        embed = message.embeds[0]

        if not embed.author or not embed.author.name:
            return

        if not embed.author.name.lower().startswith(self.bot.user.name.lower()):
            return

        has_dealer_field = any("dealer" in (field.name or "").lower() for field in embed.fields)
        if not has_dealer_field:
            return

        dealer_points, player_points, is_soft = blackjack_agent.parse_embed(embed.fields)

        if dealer_points is None or player_points is None:
            self.bot.log("WARN", f"Blackjack: Could not parse embed fields: {embed.fields}")
            return

        footer = embed.footer.text if embed.footer else ""
        if any(x in footer for x in ["You won", "You lost", "You tied", "You both bust"]):
            return

        best_move = blackjack_agent.get_best_move(dealer_points, player_points, is_soft)
        self.bot.log("INFO", f"Blackjack Agent: Dealer [{dealer_points}], Player [{player_points}{'*' if is_soft else ''}]. Move -> {best_move}")

        await asyncio.sleep(random.uniform(0.8, 2.2))

        reaction = "👊" if best_move == "HIT" else "🛑"

        try:
            await message.add_reaction(reaction)
            self.bot.log("SUCCESS", f"Blackjack: Played {best_move} (reaction {reaction})")
        except discord.errors.Forbidden:
            self.bot.log("ERROR", "Blackjack: Missing permission to add reactions.")
        except discord.errors.NotFound:
            self.bot.log("ERROR", "Blackjack: Message not found (maybe deleted).")
        except Exception as e:
            self.bot.log("ERROR", f"Blackjack reaction failed: {e}")

async def setup(bot):
    cog = ResponseHandler(bot)
    await bot.add_cog(cog)