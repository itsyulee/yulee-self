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


import asyncio
import re
import time
import random
import json
import core.state as state
from discord.ext import commands
from yulee_engines.quest_engine import YuleeQuestEngine
from component_v2_yulee import parse_v2_message
from utils.quest_tracking import message_text, parse_tracking, belongs_to_user, tracking_images

class Quest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active = True
        self._tracking_messages = {}
        self.task = None
        self.engine = YuleeQuestEngine(self.bot)

    async def register_actions(self):
        cfg = self.bot.config.get('commands', {}).get('quest', {})
        if cfg.get('enabled', True):
            self.bot.log("SYS", "Quest Module configured.")
            ih = cfg.get('interval_h', 6)
            await self.bot.yulee_register_command("quest", "quest", priority=self.bot.get_cmd_priority("quest", 4), delay=ih * 3600, initial_offset=10)
            self.trigger_action()
            
            self.engine.start()

    def trigger_action(self):
        cfg = self.bot.config.get('commands', {}).get('quest', {})
        ih = cfg.get('interval_h', 6)
        
        if 'quest' in self.bot.cmd_states:
            self.bot.cmd_states['quest']['delay'] = ih * 3600

    @commands.Cog.listener()
    async def on_socket_raw_receive(self, msg):
        if not self.active:
            return

        if isinstance(msg, bytes):
            return

        try:
            raw_data = json.loads(msg)
        except:
            return

        if raw_data.get("t") not in ["MESSAGE_CREATE", "MESSAGE_UPDATE"]:
            return

        data = raw_data.get("d", {})
        message_id = str(data.get("id", ""))
        previous = self._tracking_messages.get(message_id, {})
        data = {**previous, **data}
        if str(data.get("author", {}).get("id")) != str(self.bot.owo_bot_id):
            return
        text = message_text(data)
        parsed = parse_tracking(text)
        if parsed is None:
            return
        configured_channel = str(data.get("channel_id")) in {str(c) for c in self.bot.channels}
        if not configured_channel:
            return
        self._tracking_messages[message_id] = data
        if len(self._tracking_messages) > 100:
            del self._tracking_messages[next(iter(self._tracking_messages))]
        names = [self.bot.user.name, self.bot.display_name, getattr(self.bot.user, 'global_name', None)] + list(getattr(self.bot, 'identifiers', []))
        guild = self.bot.get_guild(int(data['guild_id'])) if data.get('guild_id') else None
        member = guild.get_member(self.bot.user.id) if guild else None
        if member:
            names.append(member.display_name)
        if not belongs_to_user(text, self.bot.user.id, names):
            return
        images = tracking_images(data)
        if not parsed[1] and images:
            kind, _, timer = parsed
            key = {'quest': 'quest_data', 'daily': 'daily_checklist_data', 'weekly': 'weekly_checklist_data'}[kind]
            self.bot.stats[key] = []
            self.bot.stats.setdefault('quest_images', {})[kind] = {
                'urls': images, 'updated_at': time.time(), 'message_id': message_id
            }
            self.bot.stats[{'quest': 'next_quest_timer', 'daily': 'daily_checklist_timer', 'weekly': 'weekly_checklist_timer'}[kind]] = timer
            self.bot.log("SYS", f"Dashboard synced: {kind} image updated.")
            return
        self._sync_tracking(text)
        if parsed[1]:
            self.bot.stats.setdefault('quest_images', {}).pop(parsed[0], None)
        if parsed[0] == 'quest' and not self.bot.paused:
            self._parse_quests_v2(parse_v2_message(data), data)

    def _sync_tracking(self, text):
        parsed = parse_tracking(text)
        if parsed is None:
            return
        kind, items, timer = parsed
        # Do not erase a good snapshot when a loading/unknown layout has no rows.
        if not items:
            self.bot.log("WARN", f"QUEST SYNC: recognized {kind}, but found no text progress rows. Text: {text[:1500]!r}")
            return
        key = {'quest': 'quest_data', 'daily': 'daily_checklist_data', 'weekly': 'weekly_checklist_data'}[kind]
        self.bot.stats[key] = items
        self.bot.stats[{'quest': 'next_quest_timer', 'daily': 'daily_checklist_timer', 'weekly': 'weekly_checklist_timer'}[kind]] = timer
        self.bot.log("SYS", f"Dashboard synced: {len(items)} {kind} tasks tracked.")

    def _parse_quests_v2(self, components, message_data):
        # Preserve auto-claim only for explicitly numbered claim button IDs.
        # A generic Claim button may open a selector; never infer its target.
        if not self.bot.config.get('commands', {}).get('quest', {}).get('auto_claim', True):
            return
        parsed = parse_tracking(message_text(message_data))
        if not parsed or parsed[0] != 'quest':
            return
        slots = {}
        for line in message_text(message_data).splitlines():
            match = re.search(r'(?:^|\s)(\d+)\.\s*(.*)', line.replace('*', ''))
            if match:
                title = re.sub(r'<a?:\w+:\d+>', '', match.group(2))
                title = re.sub(r'^[^\w]+', '', title).strip()
                slots[title] = int(match.group(1))
        completed_slots = {slots[q['description']] for q in parsed[1]
                           if q['completed'] and q['description'] in slots}
        for comp in components:
            if comp.name != 'button' or not comp.custom_id:
                continue
            match = re.search(r'claim.*?(\d+)', comp.custom_id.lower())
            if match and int(match.group(1)) in completed_slots:
                asyncio.create_task(self.bot.interactions.click_button_raw(
                    custom_id=comp.custom_id,
                    message_id=message_data.get('id'),
                    channel_id=int(message_data['channel_id']),
                    author_id=message_data['author']['id'],
                    guild_id=message_data.get('guild_id'),
                    flags=message_data.get('flags', 0)))

    @commands.Cog.listener()
    async def on_message(self, message):
        core_config = self.bot.config.get('core', {})
        monitor_id = str(core_config.get('monitor_bot_id', '408785106942164992'))
        
        if str(message.author.id) != monitor_id:
            return
        if self.bot.owo_user is None:
            self.bot.owo_user = message.author
        if str(message.channel.id) not in {str(c) for c in self.bot.channels}:
            return
        full_text = self.bot.get_full_content(message)
        if "quest log" in full_text or "checklist" in full_text:
            is_for_me = self.bot.is_message_for_me(message, role="header")
            if not is_for_me:
                return
            self._sync_tracking(full_text)

    def _parse_quests_legacy(self, text):
        progress_pattern = r'progress:\s*\[(\d+)/(\d+)\]'
        timer_pattern = r'next quest in:\s*(\d+h \d+m \d+s)'
        
        clean_text = text.replace(':blank:', '').replace('*', '')
        lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
        
        new_quest_data = []
        current_description = None
        
        st = self.bot.stats
        old_quests = st.get('quest_data', [])
        
        for i, line in enumerate(lines):
            if "reward:" in line.lower():
                desc_part = re.split(r'reward:', line, flags=re.IGNORECASE)[0].strip()
                desc_part = desc_part.replace('‣', '').strip()
                
                if desc_part:
                    raw_desc = desc_part
                else:
                    raw_desc = lines[i-1] if i > 0 else ""
                
                clean_desc = re.sub(r'^\d+[\)\.]\s*', '', raw_desc)
                clean_desc = re.sub(r'<[^>]*>', '', clean_desc)
                clean_desc = clean_desc.replace('`', '').strip()
                
                if clean_desc and 'quest log' not in clean_desc.lower() and 'quests belong' not in clean_desc.lower():
                    current_description = clean_desc
            
            progress_match = re.search(progress_pattern, line, re.IGNORECASE)
            if progress_match and current_description:
                current = int(progress_match.group(1))
                total = int(progress_match.group(2))
                
                is_completed = current >= total
                quest_item = {
                    'description': current_description,
                    'current': current,
                    'total': total,
                    'completed': is_completed
                }
                new_quest_data.append(quest_item)
                
                if is_completed:
                    was_completed = any(q['description'] == current_description and q.get('completed') for q in old_quests)
                    if not was_completed:
                        self.bot.log("SUCCESS", f"QUEST COMPLETED: {current_description}")
                
                current_description = None

        timer_match = re.search(timer_pattern, text, re.IGNORECASE)
        next_timer = timer_match.group(1).upper() if timer_match else None
        
        valid_quests = [q for q in new_quest_data if 'progress' not in q['description'].lower()]
        
        if valid_quests or "quest log" in text.lower():
            st['quest_data'] = valid_quests
            
        st['next_quest_timer'] = next_timer

async def setup(bot):
    cog = Quest(bot)
    await bot.add_cog(cog)