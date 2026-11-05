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
            "verify that you are human", "please use the link below",
            "beep boop", "i am back with", "i will be back in",
            "please include your password"
        ] # these owo mssgs does not contain our name , and some for security 

    def clean_text(self, text):
        if not text: return ""
        clean = "".join(ch for ch in text if unicodedata.category(ch)[0] != 'C')
        clean = clean.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '').replace('\ufeff', '')
        return clean.lower().strip()

    def _strip_punct(self, text):
        if not text: return ""
        return re.sub(r'[^\w\s]', '', text.lower()).strip()

    def _collect_identifiers(self, message=None):
        raw_idents = set()
        clean_idents = set()

        candidates = [
            getattr(self.bot.user, 'name', None) if getattr(self.bot, 'user', None) else None,
            getattr(self.bot.user, 'display_name', None) if getattr(self.bot, 'user', None) else None,
            getattr(self.bot.user, 'global_name', None) if getattr(self.bot, 'user', None) else None,
            getattr(self.bot, 'username', None),
            getattr(self.bot, 'display_name', None),
        ] + list(getattr(self.bot, 'identifiers', []))

        # Also include configured account name from accounts.json if matched
        uid = str(getattr(self.bot.user, 'id', getattr(self.bot, 'user_id', '')) or '')
        for acc in getattr(self.bot, 'accounts', []):
            if isinstance(acc, dict):
                acc_token = acc.get('token')
                acc_id = str(acc.get('id', acc.get('user_id', '')) or '')
                if (uid and acc_id == uid) or (acc_token and acc_token == getattr(self.bot, 'token', None)):
                    if acc.get('name'):
                        candidates.append(acc['name'])

        if message and getattr(message, 'guild', None) and getattr(self.bot, 'user', None):
            member = message.guild.get_member(self.bot.user.id)
            if member:
                if getattr(member, 'nick', None):
                    candidates.append(member.nick)
                if getattr(member, 'display_name', None):
                    candidates.append(member.display_name)

        for item in candidates:
            if not item or not isinstance(item, str):
                continue
            cleaned_raw = self.clean_text(item)
            if cleaned_raw and not cleaned_raw.startswith('<@'):
                raw_idents.add(cleaned_raw)
            stripped = self._strip_punct(cleaned_raw)
            if stripped and len(stripped) >= 2:
                clean_idents.add(stripped)

        return raw_idents, clean_idents

    def is_message_for_me(self, message, role="any", keyword=None):
        if not message or not getattr(self.bot, 'user', None):
            return False

        uid = str(self.bot.user.id)
        try:
            if self.bot.user.mentioned_in(message):
                return True
        except Exception:
            pass

        raw_content = message.content or ""
        if f"<@{uid}>" in raw_content or f"<@!{uid}>" in raw_content:
            return True

        raw_idents, clean_idents = self._collect_identifiers(message)

        content = self.clean_text(raw_content)
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
                if f"<@{uid}>" in text or f"<@!{uid}>" in text:
                    return True
                for r_ident in raw_idents:
                    if re.search(rf"(?<!\w){re.escape(r_ident)}(?:'s|’s)?(?!\w)", text):
                        return True
                stripped_text = self._strip_punct(text)
                for ident in clean_idents:
                    if re.search(rf"\b{re.escape(ident)}(?:s)?\b", stripped_text):
                        return True
            return False

        if role in ["source", "target"] and keyword:
            keyword = keyword.lower()
            if keyword in content:
                parts = content.split(keyword, 1)
                check_text = parts[0] if role == "source" else parts[1]
                if f"<@{uid}>" in check_text or f"<@!{uid}>" in check_text:
                    return True
                for r_ident in raw_idents:
                    if r_ident in check_text:
                        return True
                stripped_check = self._strip_punct(check_text)
                for ident in clean_idents:
                    if re.search(rf"\b{re.escape(ident)}\b", stripped_check):
                        return True
            return False

        texts = [content]
        if message.embeds:
            for em in message.embeds:
                fields_text = " ".join([f"{f.name} {f.value}" for f in em.fields])
                raw_embed_text = f"{em.title or ''} {em.author.name if em.author else ''} {em.description or ''} {fields_text}"
                texts.append(self.clean_text(raw_embed_text))

        for text in texts:
            if f"<@{uid}>" in text or f"<@!{uid}>" in text:
                return True
            for r_ident in raw_idents:
                if re.search(rf"(?<!\w){re.escape(r_ident)}(?!\w)", text, re.I):
                    return True
                if len(r_ident) > 3 and r_ident in text:
                    return True
            stripped_text = self._strip_punct(text)
            for ident in clean_idents:
                if re.search(rf"\b{re.escape(ident)}\b", stripped_text, re.I):
                    return True
                if ident in stripped_text and len(ident) > 3:
                    return True

        full_visible_text = " ".join(texts)
        stripped_full = self._strip_punct(full_visible_text)
        if any(pat in full_visible_text for pat in self.generic_patterns):
            if not message.guild:
                return True
            for r_ident in raw_idents:
                if r_ident in full_visible_text:
                    return True
            for ident in clean_idents:
                if ident in stripped_full:
                    return True
            return False

        return False
