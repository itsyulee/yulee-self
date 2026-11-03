import asyncio
import glob
import json
import os
import random
import re
import time
import discord
from discord.ext import commands
import core.state as state
from component_v2_yulee import get_boss_battle_id, parse_v2_message


class Boss(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.state_file = self._get_state_file()
        self._load_state()
        self._ensure_dashboard_config_schema()
        self._sync_config()

        self.playing_guild_ids = set()
        self._update_playing_guilds()

    def _get_state_file(self):
        uid = getattr(self.bot, "user_id", None) or (
            str(self.bot.user.id) if getattr(self.bot, "user", None) else None
        )
        if uid:
            return os.path.join(state.DATA_DIR, f"boss_state_{uid}.json")
        return os.path.join(state.DATA_DIR, "boss_state.json")

    def _ensure_dashboard_config_schema(self):
        """Tự động bổ sung trường 'channels': [] vào mục 'boss' trong defaults và tất cả file config/settings*.json
        để Web Dashboard hiển thị ngay mục Channels trong phần Categories -> BOSS."""
        if isinstance(self.bot.config.get("boss"), dict):
            self.bot.config["boss"].setdefault("channels", [])

        config_files = [
            os.path.join(state.CODE_DIR, "defaults", "settings.json"),
            os.path.join(state.CONFIG_DIR, "settings.json"),
            "defaults/settings.json",
            "config/settings.json",
        ]
        config_files.extend(glob.glob(os.path.join(state.CONFIG_DIR, "settings_*.json")))
        config_files.extend(glob.glob("config/settings_*.json"))

        seen = set()
        for path in config_files:
            abs_p = os.path.abspath(path)
            if abs_p in seen or not os.path.exists(abs_p):
                continue
            seen.add(abs_p)
            try:
                with open(abs_p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data.get("boss"), dict) and "channels" not in data["boss"]:
                    data["boss"]["channels"] = []
                    with open(abs_p, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception:
                continue

    def _sync_config(self):
        boss_cfg = self.bot.config.get("boss", {})
        self.enabled = boss_cfg.get("enabled", True)
        self.join_chance = boss_cfg.get("join_chance", 100)
        self.join_all = boss_cfg.get("join_all_guilds", True)
        self.ignore_guilds = [
            str(g).strip() for g in boss_cfg.get("ignore_guilds", []) if str(g).strip()
        ]
        # Đọc danh sách kênh chỉ định từ trường "channels" trên Web Dashboard (Categories -> BOSS -> Channels)
        raw_channels = boss_cfg.get("channels", boss_cfg.get("target_channels", []))
        if isinstance(raw_channels, str):
            raw_channels = [c.strip() for c in re.split(r"[\s,]+", raw_channels) if c.strip()]
        self.target_channels = [
            str(c).strip() for c in (raw_channels or []) if str(c).strip()
        ]

    def _update_playing_guilds(self):
        self.playing_guild_ids.clear()
        all_channels = list(getattr(self.bot, "channels", [])) + list(self.target_channels)
        for c_id in all_channels:
            try:
                ch = self.bot.get_channel(int(c_id))
                if ch and getattr(ch, "guild", None):
                    self.playing_guild_ids.add(str(ch.guild.id))
            except (ValueError, TypeError):
                continue

        if hasattr(self.bot, "guild_id") and self.bot.guild_id:
            self.playing_guild_ids.add(str(self.bot.guild_id))

    async def _subscribe_target_channels(self):
        """Fetch và subscribe vào các kênh/guild đánh boss để Discord Gateway đẩy sự kiện MESSAGE_CREATE về."""
        for c_id in self.target_channels:
            if not c_id.isdigit():
                continue
            try:
                ch = self.bot.get_channel(int(c_id))
                if not ch:
                    ch = await self.bot.fetch_channel(int(c_id))
                if ch and getattr(ch, "guild", None):
                    self.playing_guild_ids.add(str(ch.guild.id))
                    try:
                        if hasattr(ch.guild, "subscribe"):
                            await ch.guild.subscribe()
                    except Exception:
                        pass
            except Exception as e:
                self.bot.log("WARN", f"Auto Boss: Cannot access channel {c_id}: {e}")

    async def register_actions(self):
        self.state_file = self._get_state_file()
        self._load_state()
        self._check_reset()
        self._ensure_dashboard_config_schema()
        self._sync_config()
        await self._subscribe_target_channels()
        self._update_playing_guilds()
        if self.enabled:
            if self.target_channels:
                self.bot.log(
                    "BOSS",
                    f"Auto Boss active on designated channels: {', '.join(self.target_channels)} (Tickets: {self.tickets}/3)",
                )
            else:
                mode = "All Guilds" if self.join_all else "Playing Guilds"
                self.bot.log(
                    "BOSS",
                    f"Auto Boss active ({mode}, Tickets: {self.tickets}/3)",
                )

    def _load_state(self):
        self.tickets = 3
        self.last_reset = 0
        self.joined_ids = set()

        # Chỉ đọc file boss_state_<uid>.json riêng của tài khoản, KHÔNG fallback sang boss_state.json chung
        # bị dính timestamp ảo 1791952100 và tickets=0 từ source gốc
        path = self.state_file
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    last_reset = float(data.get("last_reset", 0) or 0)
                    now = time.time()
                    # Nếu file lưu timestamp tương lai bất thường (> now + 60) thì reset lại 3 vé
                    if last_reset > now + 60:
                        self.tickets = 3
                        self.last_reset = now
                        self.joined_ids = set()
                    else:
                        self.tickets = int(data.get("tickets", 3))
                        self.last_reset = last_reset
                        self.joined_ids = set(data.get("joined_ids", []))
            except Exception:
                pass

    def _save_state(self):
        try:
            self.state_file = self._get_state_file()
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "tickets": self.tickets,
                        "last_reset": self.last_reset,
                        "joined_ids": list(self.joined_ids)[-200:],
                    },
                    f,
                    indent=4,
                )
        except Exception:
            pass

    def _check_reset(self):
        now = time.time()
        # Nếu last_reset bị lệch sang tương lai hoặc đã qua 20 giờ (72000s) -> reset lại 3 vé
        if self.last_reset > now + 60 or (self.last_reset > 0 and now - self.last_reset >= 72000):
            self.tickets = 3
            self.last_reset = now
            self.joined_ids.clear()
            self._save_state()
        elif self.last_reset == 0:
            self.last_reset = now
            self._save_state()

    def _sync_tickets_from_text(self, text, is_for_me=False):
        """Trích xuất số vé boss (VD: 'you currently have 2/3 boss tickets!' hoặc 'ran out of boss tickets')
        và thời gian hồi vé (<t:TIMESTAMP:R>) từ cả embed, content hoặc V2 component."""
        low = (text or "").lower()
        if "boss ticket" not in low:
            return False

        if not is_for_me:
            clean_txt = self.bot.identity.clean_text(text) if hasattr(self.bot, "identity") else low
            clean_idents, raw_idents = (
                self.bot.identity._build_idents()
                if hasattr(self.bot, "identity")
                else (set(), set())
            )
            uid = str(getattr(self.bot, "user_id", "") or (self.bot.user.id if getattr(self.bot, "user", None) else ""))
            if uid and (f"<@{uid}>" in low or f"<@!{uid}>" in low):
                is_for_me = True
            else:
                for r_id in raw_idents:
                    if r_id and r_id in clean_txt:
                        is_for_me = True
                        break
                if not is_for_me:
                    text_alnum = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", clean_txt)).strip()
                    for c_id in clean_idents:
                        if c_id and (c_id in text_alnum):
                            is_for_me = True
                            break

        if not is_for_me:
            return False

        # Kiểm tra nếu trong tin nhắn có timestamp hồi vé của Discord: Replenishes <t:1730000000:R>
        ts_match = re.search(r"<t:(\d+)(?::[a-zA-Z])?>", text or "")
        now = time.time()

        match = re.search(r"(\d+)\s*/\s*3\s*boss\s*ticket", low)
        if match:
            new_tickets = int(match.group(1))
            self.tickets = new_tickets
            if ts_match:
                replenish_at = int(ts_match.group(1))
                # _check_reset cộng 72000s từ last_reset, nên đặt last_reset = replenish_at - 72000
                self.last_reset = max(0, replenish_at - 72000)
            else:
                self.last_reset = now
            self._save_state()
            self.bot.log("BOSS", f"Synced boss tickets: {self.tickets}/3")
            return True
        elif "ran out of boss tickets" in low or "don't have any boss tickets" in low or "no boss tickets" in low:
            self.tickets = 0
            if ts_match:
                replenish_at = int(ts_match.group(1))
                self.last_reset = max(0, replenish_at - 72000)
            else:
                self.last_reset = now
            self._save_state()
            self.bot.log("BOSS", "Synced boss tickets: 0/3 (Out of tickets)")
            return True
        return False

    def get_dashboard_status(self):
        self._check_reset()
        self._sync_config()
        return {
            "enabled": bool(self.enabled),
            "tickets": self.tickets,
            "max_tickets": 3,
            "channels": self.target_channels,
            "join_all_guilds": bool(self.join_all),
            "join_chance": self.join_chance,
            "last_reset": self.last_reset,
        }

    @commands.Cog.listener()
    async def on_message(self, message):
        if str(message.author.id) != str(self.bot.owo_bot_id):
            return

        # Cho phép bắt lệnh `o boss t` hoặc thông báo vé boss ở bất kỳ kênh nào khi người dùng gõ kiểm tra
        full_content = self.bot.get_full_content(message)
        if "boss ticket" in full_content.lower():
            is_mine = self.bot.is_message_for_me(message)
            self._sync_tickets_from_text(full_content, is_for_me=is_mine)

    @commands.Cog.listener()
    async def on_socket_raw_receive(self, msg):
        # Đồng bộ lại cấu hình mới nhất từ bộ nhớ (khi người dùng bấm Save trên Web Dashboard)
        self._sync_config()
        if isinstance(msg, bytes):
            return

        try:
            payload = json.loads(msg)
        except Exception:
            return

        if payload.get("t") not in ("MESSAGE_CREATE", "MESSAGE_UPDATE"):
            return

        data = payload.get("d", {})
        if str(data.get("author", {}).get("id")) != str(self.bot.owo_bot_id):
            return

        components = parse_v2_message(data)
        v2_text = " ".join(
            getattr(c, "content", "") or "" for c in (components or [])
        )
        msg_content = data.get("content") or ""
        embed_parts = []
        for em in data.get("embeds") or []:
            embed_parts.extend([
                em.get("title") or "",
                (em.get("author") or {}).get("name") or "",
                em.get("description") or "",
            ])
            for fld in em.get("fields") or []:
                embed_parts.extend([fld.get("name") or "", fld.get("value") or ""])
        combined_raw = " ".join([msg_content, v2_text] + embed_parts)
        combined_text = combined_raw.lower()

        # Luôn đồng bộ vé boss ngay khi người dùng gõ `o boss t` hoặc khi OwO phản hồi vé boss (kể cả ở kênh bất kỳ)
        if "boss ticket" in combined_text:
            self._sync_tickets_from_text(combined_raw, is_for_me=False)

        if not self.enabled or self.bot.paused or not components:
            return

        fight_btn = next(
            (
                c
                for c in components
                if getattr(c, "custom_id", None) == "guildboss_fight"
                or (
                    getattr(c, "name", None) == "button"
                    and "guildboss" in (getattr(c, "custom_id", "") or "").lower()
                )
            ),
            None,
        )
        if not fight_btn and "runs away" not in combined_text and "guild boss" not in combined_text:
            return

        channel_id = int(data.get("channel_id", 0))
        guild_id = str(data.get("guild_id") or "")

        # 1. Bỏ qua nếu thuộc server bị chặn trong ignore_guilds
        if guild_id in self.ignore_guilds:
            return

        # 2. Kiểm tra điều kiện kênh / server được phép tham gia
        can_join = False
        if self.target_channels:
            # Nếu trong Categories -> BOSS -> Channels có thêm ID kênh -> CHỈ đánh ở các kênh đó
            if str(channel_id) in self.target_channels:
                can_join = True
        else:
            # Nếu để trống Channels (No items added) -> hoạt động theo cấu hình mặc định
            if self.join_all:
                can_join = True
            else:
                configured_channels = [str(c) for c in getattr(self.bot, "channels", [])]
                if (
                    str(channel_id) in configured_channels
                    or str(channel_id) == str(self.bot.channel_id)
                ):
                    can_join = True
                elif guild_id in self.playing_guild_ids:
                    can_join = True

        if not can_join or not fight_btn or getattr(fight_btn, "disabled", False):
            return

        battle_id = get_boss_battle_id(components) or str(data.get("id"))
        if battle_id in self.joined_ids:
            return

        self._check_reset()
        if self.tickets <= 0:
            return

        if random.randint(1, 100) > self.join_chance:
            self.joined_ids.add(battle_id)
            self._save_state()
            return

        await asyncio.sleep(random.uniform(0.5, 1.5))
        if self.bot.paused:
            return

        success = await self.bot.interactions.click_button_raw(
            custom_id=fight_btn.custom_id,
            message_id=data.get("id"),
            channel_id=channel_id,
            author_id=data.get("author", {}).get("id"),
            guild_id=guild_id,
            flags=data.get("flags", 0),
        )

        if success:
            self.tickets = max(0, self.tickets - 1)
            self.joined_ids.add(battle_id)
            self._save_state()
            self.bot.log(
                "SUCCESS",
                f"Joined Boss Battle in channel {channel_id} (Tickets left: {self.tickets}/3)",
            )
        else:
            self.bot.log("ERROR", f"Failed to join Boss Battle in channel {channel_id}.")


async def setup(bot):
    await bot.add_cog(Boss(bot))
