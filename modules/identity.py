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


import re
import unicodedata

class IdentityManager:
    def __init__(self, bot):
        self.bot = bot
        self.generic_patterns = [
            "are you a real human", "complete your captcha",
            "verify that you are human", "please use the link below"
        ] # security messages that may not contain our name in DMs

    def clean_text(self, text):
        if not text: return ""
        text = unicodedata.normalize("NFKC", text)
        clean = "".join(ch for ch in text if unicodedata.category(ch)[0] != 'C')
        clean = clean.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '').replace('\ufeff', '')
        return clean.lower().strip()

    def learn_author_identity(self, author):
        """Learn guild nickname / display_name from our own sent messages."""
        if not author or not getattr(self.bot, 'user', None):
            return
        if getattr(author, 'id', None) != self.bot.user.id:
            return
        if not hasattr(self.bot, 'identifiers') or self.bot.identifiers is None:
            self.bot.identifiers = []
        for attr in ('name', 'display_name', 'global_name', 'nick'):
            val = getattr(author, attr, None)
            if val and isinstance(val, str):
                low = val.lower().strip()
                if low and low not in self.bot.identifiers:
                    self.bot.identifiers.append(low)

    def _build_idents(self, message=None):
        global_name = getattr(self.bot.user, 'global_name', None)
        user_disp = getattr(self.bot.user, 'display_name', None)
        idents = [self.bot.user.name, self.bot.display_name, user_disp, global_name] + getattr(self.bot, 'identifiers', [])
        if message and getattr(message, 'guild', None):
            member = message.guild.get_member(self.bot.user.id) or getattr(message.guild, 'me', None)
            if member:
                idents.extend([getattr(member, 'nick', None), getattr(member, 'display_name', None)])

        clean_idents = set()
        raw_idents = set()
        for i in idents:
            if not i or not isinstance(i, str) or i.startswith("<@"):
                continue
            norm_i = self.clean_text(i)
            if not norm_i:
                continue
            ci = re.sub(r'[^\w\s]', '', norm_i).strip()
            ci = re.sub(r'\s+', ' ', ci)
            if ci and len(ci) >= 2:
                clean_idents.add(ci)
            ri = re.sub(r'[*_`~|<>]', '', norm_i).strip()
            if ri and len(ri) >= 2:
                raw_idents.add(ri)
        return clean_idents, raw_idents

    def is_message_for_me(self, message, role="any", keyword=None):
        if not message:
            return False
        
        if self.bot.user.mentioned_in(message): 
            return True

        clean_idents, raw_idents = self._build_idents(message)

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
            
            for raw_hdr in header_texts:
                for r_ident in raw_idents:
                    if r_ident in raw_hdr:
                        return True
                text = re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', raw_hdr)).strip()
                for ident in clean_idents:
                    if re.search(rf"\b{re.escape(ident)}(?:s)?\b", text):
                        return True
            return False

        if role in ["source", "target"] and keyword:
            keyword = self.clean_text(keyword)
            if keyword in content:
                parts = content.split(keyword, 1)
                check_text = parts[0] if role == "source" else parts[1]
                check_clean = re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', check_text)).strip()
                for ident in clean_idents:
                    if re.search(rf"\b{re.escape(ident)}\b", check_clean):
                        return True
                for r_ident in raw_idents:
                    if r_ident in check_text:
                        return True
            return False

        texts = [content]
        if message.embeds:
            for em in message.embeds:
                fields_text = " ".join([f"{f.name} {f.value}" for f in em.fields])
                raw_embed_text = f"{em.title or ''} {em.author.name if em.author else ''} {em.description or ''} {fields_text}"
                texts.append(self.clean_text(raw_embed_text))

        for text in texts:
            text_clean = re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', text)).strip()
            for ident in clean_idents:
                if re.search(rf"\b{re.escape(ident)}\b", text_clean, re.I):
                    return True
                if ident in text_clean and len(ident) > 3:
                    return True
            for r_ident in raw_idents:
                if r_ident in text and len(r_ident) >= 2:
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
