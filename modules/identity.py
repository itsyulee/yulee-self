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


import re
import unicodedata

class IdentityManager:
    def __init__(self, bot):
        self.bot = bot
        self.generic_patterns = [
            "are you a real human", "complete your captcha",
            "verify that you are human", "please use the link below",
            "beep boop", "i am back with", "i will be back in",
            "please include your password"
        ] # these owo mssgs does not contain our name , and some for security 

    def clean_text(self, text):
        if not text: return ""
        clean = "".join(ch for ch in text if unicodedata.category(ch)[0] != 'C')
        clean = clean.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '').replace('\ufeff', '')
        return clean.lower().strip()

    def is_message_for_me(self, message, role="any", keyword=None):
        if not message:
            return False
        
        if self.bot.user.mentioned_in(message): 
            return True

        idents = [self.bot.user.name, self.bot.display_name] + getattr(self.bot, 'identifiers', [])
        clean_idents = set()
        for i in idents:
            ci = re.sub(r'[^\w\s]', '', i.lower()).strip()
            if ci and len(ci) >= 2:
                clean_idents.add(ci)
            
        if message.guild:
            member = message.guild.get_member(self.bot.user.id)
            if member and member.nick:
                nick = member.nick.lower()
                clean_nick = re.sub(r'[^\w\s]', '', nick).strip()
                if clean_nick:
                    clean_idents.add(clean_nick)

        content = self.clean_text(message.content)
        if role == "header":
            first_line = content.split('\n')[0]
            header_texts = [first_line]
            if message.embeds:
                for em in message.embeds:
                    if em.title:
                        header_texts.append(self.clean_text(em.title))
                    if em.author and em.author.name:
                        header_texts.append(self.clean_text(em.author.name))
                    if em.description:
                        header_texts.append(self.clean_text(em.description.split('\n')[0]))
            
            for text in header_texts:
                for ident in clean_idents:
                    if re.search(rf"\b{re.escape(ident)}(?:'s)?\b", text):
                        return True
            return False

        if role in ["source", "target"] and keyword:
            keyword = keyword.lower()
            if keyword in content:
                parts = content.split(keyword, 1)
                check_text = parts[0] if role == "source" else parts[1]
                for ident in clean_idents:
                    if re.search(rf"\b{re.escape(ident)}\b", check_text):
                        return True
            return False

        texts = [content]
        if message.embeds:
            for em in message.embeds:
                fields_text = " ".join([f"{f.name} {f.value}" for f in em.fields])
                raw_embed_text = f"{em.title or ''} {em.author.name if em.author else ''} {em.description or ''} {fields_text}"
                texts.append(self.clean_text(raw_embed_text))

        for text in texts:
            for ident in clean_idents:
                if re.search(rf"\b{re.escape(ident)}\b", text, re.I):
                    return True
                if ident in text and len(ident) > 3:
                    return True

        full_visible_text = " ".join(texts)
        if any(pat in full_visible_text for pat in self.generic_patterns):
            if not message.guild or self.bot.user.mentioned_in(message):
                return True
            for ident in clean_idents:
                if ident in full_visible_text:
                    return True
            return False

        return False

