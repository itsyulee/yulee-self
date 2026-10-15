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
import core.state as state

# quest intelligence is still under testing , errors and bugs can occur


# ─────────────────────────────────────────────────────────────────────────────
#        owo quest type (taken from owobot src ) 
# ─────────────────────────────────────────────────────────────────────────────
# self quests (no alt needed):
#   hunt         → "manually hunt X times!"
#   battle       → "battle X times!"             
#   gamble       → "gamble X times!"             
#   owo          → "say 'owo' X times!"        
#   find         → "hunt 3 animals that are X rank!"  
#   xp           → "earn X xp from hunting and battling!"  (normal grinding)
#   emoteTo      → "use an action command on someone X times!"  hug/f*ck(owobot)/etc
#
# alt quests (requires alt account):
#   emoteBy      → "have a friend use an action command on you X times!"
#   prayBy       → "have a friend pray to you X times!"
#   curseBy      → "have a friend curse you X times!"
#   cookieBy     → "receive a cookie from X friends!"
#   friendlyBattle → "battle with a friend X times!"
# ─────────────────────────────────────────────────────────────────────────────


EMOTE_COMMANDS = ["hug", "poke", "pat", "cuddle", "kiss"]

FALLBACK_TARGETS = ["408785106942164992"]

class NeuraQuestEngine:
    def __init__(self, bot):
        self.bot = bot
        self.last_solver_run = 0
        self.solver_task = None
        self._alt_warned = False
        self.last_signaled = {}
        self.last_queued = {}

    def start(self):
        if not self.solver_task:
            self.solver_task = asyncio.create_task(self._quest_solver_loop())

    async def _quest_solver_loop(self):
        await asyncio.sleep(15)  
        while True:
            if not getattr(self.bot, 'is_ready', False) or getattr(self.bot, 'paused', False):
                await asyncio.sleep(5)
                continue

            now = time.time()
            if now - self.last_solver_run < 20: 
                await asyncio.sleep(2)
                continue

            self.last_solver_run = now
            st = self.bot.stats
            quests = st.get('quest_data', [])

            has_rarity_quest = any(
                "hunt 3 animals that are" in q.get('description', '')
                and not q.get('completed', False)
                for q in quests
            )
            if not has_rarity_quest and st.get('force_lucky_gems'):
                st['force_lucky_gems'] = False
                self.bot.log("SYS", "Quest Engine: Rarity quest done — disabled Force Lucky Gems.")

            for q in quests:
                if q.get('completed', False):
                    continue

                desc = q.get('description', '').lower()
                current = q.get('current', 0)
                total = q.get('total', 1)
                remaining = total - current

                # priorty 1: social quests that need an alt account 
                if self.is_alt_quest(desc):
                    now = time.time()
                    if now - self.last_signaled.get(desc, 0) < 60:
                        break 
                    cfg = self.bot.config.get('commands', {}).get('quest', {})
                    if cfg.get('use_alt_account', True):
                        instances = getattr(state, 'bot_instances', [])
                        if len(instances) > 1:
                            self.last_signaled[desc] = now
                            await self._signal_alt(desc)
                        else:
                            if not self._alt_warned:
                                self.bot.log(
                                    "WARN",
                                    "Quest Engine: Social quest active but no alt accounts online. "
                                    f"Quest: '{q.get('description', '')}'"
                                )
                                self._alt_warned = True
                    break  

                # priorty 2: self-contained quests we automate directly ──

                elif "gamble" in desc:
                    await self._queue_quest_command("owo cf 1", "Gamble Quest", cooldown=12)
                    break

                elif "use an action command on someone" in desc or "use an emote command on someone" in desc:
                    target_id = self._get_sibling_or_fallback()
                    emote = random.choice(EMOTE_COMMANDS)
                    await self._queue_quest_command(
                        f"owo {emote} <@{target_id}>",
                        "Action/Emote Quest",
                        cooldown=8
                    )
                    break

                elif "hunt 3 animals that are" in desc and not st.get('force_lucky_gems'):
                    st['force_lucky_gems'] = True
                    self.bot.log("SYS", "Quest Engine: Enabled Force Lucky Gems for rarity quest.")

                elif "say 'owo'" in desc or "say \"owo\"" in desc:
                    if remaining > 5:
                        await self._queue_quest_command("owo", "OWO Quest", cooldown=6)
                    break

                # hunt / battle / xp quests are handled by the grinding loop.


            await asyncio.sleep(5)

    # ──────────────────────────────────────────────────────────────────────────
    #  helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _get_sibling_or_fallback(self):
        instances = getattr(state, 'bot_instances', [])
        if len(instances) > 1:
            sibling = next(
                (inst for inst in instances if str(inst.user.id) != str(self.bot.user_id)),
                None
            )
            if sibling:
                return sibling.user.id
        return random.choice(FALLBACK_TARGETS)

    async def _queue_quest_command(self, cmd, reason, cooldown=10):
        now = time.time()
        if now - self.last_queued.get(cmd, 0) < cooldown:
            return  
        self.last_queued[cmd] = now
        self.bot.log("SYS", f"Quest Engine: Queueing [{cmd}] for {reason}")
        await self.bot.neura_enqueue(cmd, priority=5)

    def is_alt_quest(self, desc):
        socials = [
            "have a friend use an action command on you",
            "have a friend use an emote command on you",
            "have a friend pray to you",
            "have a friend curse you",
            "receive a cookie from",
            "battle with a friend",
        ]
        return any(s in desc for s in socials)

    async def _signal_alt(self, desc):
        my_id = self.bot.user_id

        target_cmd = None
        if "pray to you" in desc:
            target_cmd = f"owo pray <@{my_id}>"
        elif "curse you" in desc:
            target_cmd = f"owo curse <@{my_id}>"
        elif "action command on you" in desc or "emote command on you" in desc:
            emote = random.choice(EMOTE_COMMANDS)
            target_cmd = f"owo {emote} <@{my_id}>"
        elif "cookie from" in desc:
            target_cmd = f"owo cookie <@{my_id}>"

        for instance in getattr(state, 'bot_instances', []):
            is_other = str(instance.user.id) != str(my_id)
            is_active = getattr(instance, 'is_ready', False) and not getattr(instance, 'paused', False)
            if not (is_other and is_active):
                continue

            if "battle with a friend" in desc:
                await self.bot.neura_enqueue(f"owo battle <@{instance.user.id}>", priority=5)

                async def delayed_ab(inst=instance):
                    await asyncio.sleep(4.0)
                    await inst.neura_enqueue("owo ab", priority=4, target_channel_id=self.bot.channel_id)

                asyncio.create_task(delayed_ab())
                self.bot.log("SYS", f"Quest Engine: Coordinated friendly battle with {instance.user.name}")
            elif target_cmd:
                await instance.neura_enqueue(target_cmd, priority=5, target_channel_id=self.bot.channel_id)
                self.bot.log("SYS", f"Quest Engine: Signalled alt {instance.user.name} → [{target_cmd}]")
            break 
