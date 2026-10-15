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
import random
import json
import core.state as state
from discord.ext import commands
from neura_engines.quest_engine import NeuraQuestEngine
from component_v2_neura import parse_v2_message

class Quest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active = True
        self.task = None
        self.engine = NeuraQuestEngine(self.bot)

    async def register_actions(self):
        cfg = self.bot.config.get('commands', {}).get('quest', {})
        if cfg.get('enabled', True):
            self.bot.log("SYS", "Quest Module configured.")
            ih = cfg.get('interval_h', 6)
            await self.bot.neura_register_command("quest", "quest", priority=self.bot.get_cmd_priority("quest", 4), delay=ih * 3600, initial_offset=10)
            self.trigger_action()
            
            self.engine.start()

    def trigger_action(self):
        cfg = self.bot.config.get('commands', {}).get('quest', {})
        ih = cfg.get('interval_h', 6)
        
        if 'quest' in self.bot.cmd_states:
            self.bot.cmd_states['quest']['delay'] = ih * 3600

    @commands.Cog.listener()
    async def on_socket_raw_receive(self, msg):
        if not self.active or self.bot.paused:
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
        if str(data.get("author", {}).get("id")) != self.bot.owo_bot_id:
            return

        components = parse_v2_message(data)
        if not components:
            return

        v2_text = " ".join([c.content for c in components if c.name in ["text_display", "section"]]).lower()
        content = (data.get("content") or "").lower()
        full_text = f"{content} {v2_text}"

        if "quest log" in full_text or "checklist" in full_text:
            idents = [self.bot.user.name.lower(), self.bot.display_name.lower()] + [i.lower() for i in getattr(self.bot, 'identifiers', [])]
            is_for_me = False
            for ident in idents:
                clean_ident = ident.replace("<@", "").replace(">", "").replace("!", "")
                if clean_ident in full_text:
                    is_for_me = True
                    break

            if not is_for_me:
                return

            self._parse_quests_v2(components, data)

    def _parse_quests_v2(self, components, message_data):
        text_lines = []
        for comp in components:
            if comp.name in ["text_display", "section"] and comp.content:
                text_lines.extend([line.strip().lower() for line in comp.content.split('\n') if line.strip()])

        quests = []
        current_quest = None
        claim_buttons = {}
        for comp in components:
            if comp.name == "button" and comp.custom_id:
                cid = comp.custom_id.lower()
                
                match = re.search(r'claim.*?(\d+)', cid)
                if match:
                    slot_num = int(match.group(1))
                    claim_buttons[slot_num] = comp.custom_id
                elif "claim" in cid:
                    pass

        for i, line in enumerate(text_lines):
            title_match = re.search(r'\b(\d+)\.\s*(.*)', line)
            if title_match:
                slot = int(title_match.group(1))
                title = title_match.group(2)
                desc = ""
                if i + 1 < len(text_lines):
                    desc = text_lines[i+1]

                current_quest = {
                    'slot': slot,
                    'description': desc,
                    'title': title,
                    'current': 0,
                    'total': 1,
                    'completed': False
                }
                quests.append(current_quest)

            elif "/" in line and current_quest:
                progress_match = re.search(r'\b(\d+)/(\d+)\b', line)
                if progress_match:
                    current_quest['current'] = int(progress_match.group(1))
                    current_quest['total'] = int(progress_match.group(2))
                    current_quest['completed'] = current_quest['current'] >= current_quest['total']
                    current_quest = None

        st = self.bot.stats
        old_quests = st.get('quest_data', [])
        
        cleaned_quests = []
        for q in quests:
            desc_text = q['description']
            # description mapping
            cleaned_quests.append({
                'description': desc_text,
                'current': q['current'],
                'total': q['total'],
                'completed': q['completed']
            })

            if q['completed']:
                was_completed = any(oq.get('description', '').lower() == desc_text.lower() and oq.get('completed') for oq in old_quests)
                if not was_completed:
                    self.bot.log("SUCCESS", f"QUEST COMPLETED: {desc_text}")
        
        if cleaned_quests:
            st['quest_data'] = cleaned_quests
            self.bot.log("SYS", f"Dashboard synced: {len(cleaned_quests)} V2 quests tracked.")

        #  global timer in v2 text lines
        timer_pattern = r'next quest.*?\bin\s*(\d+\w+(?:\s*\d+\w+)*)'
        for line in text_lines:
            timer_match = re.search(timer_pattern, line)
            if timer_match:
                st['next_quest_timer'] = timer_match.group(1).upper()
                break

        cfg = self.bot.config.get('commands', {}).get('quest', {})
        if cfg.get('auto_claim', True):
            channel_id = int(message_data.get("channel_id"))
            for q in quests:
                if q['completed']:
                    slot = q['slot']
                    if slot in claim_buttons:
                        custom_id = claim_buttons[slot]
                        self.bot.log("SUCCESS", f"Quest Engine: Auto-claiming completed quest slot {slot}...")
                        asyncio.create_task(self.bot.interactions.click_button_raw(
                            custom_id=custom_id,
                            message_id=message_data.get("id"),
                            channel_id=channel_id,
                            author_id=message_data.get("author", {}).get("id"),
                            guild_id=message_data.get("guild_id"),
                            flags=message_data.get("flags", 0)
                        ))

    @commands.Cog.listener()
    async def on_message(self, message):
        core_config = self.bot.config.get('core', {})
        monitor_id = str(core_config.get('monitor_bot_id', '408785106942164992'))
        
        if str(message.author.id) != monitor_id:
            return
        if self.bot.owo_user is None:
            self.bot.owo_user = message.author
        all_channels = [str(c) for c in self.bot.channels]
        if str(message.channel.id) not in all_channels:
            return

        full_text = self.bot.get_full_content(message)
        if ("quest log" in full_text or "checklist" in full_text) and not message.components:
            is_for_me = self.bot.is_message_for_me(message, role="header")
            if not is_for_me:
                return
            self._parse_quests_legacy(full_text)

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