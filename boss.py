import asyncio
import glob
import json
import os
import random
import re
import time
import discord
from discord.ext import commands
from component_v2_yulee import get_boss_battle_id, parse_v2_message


class Boss(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.state_file = "data/boss_state.json"
        self._load_state()
        self._ensure_dashboard_config_schema()
        self._sync_config()

        self.playing_guild_ids = set()
        self._update_playing_guilds()

    def _ensure_dashboard_config_schema(self):
        """Tự động bổ sung trường 'channels': [] vào mục 'boss' trong defaults và tất cả file config/settings*.json
        để Web Dashboard hiển thị ngay mục Channels trong phần Categories -> BOSS."""
        if isinstance(self.bot.config.get("boss"), dict):
            self.bot.config["boss"].setdefault("channels", [])

        config_files = ["defaults/settings.json", "config/settings.json"]
        config_files.extend(glob.glob("config/settings_*.json"))

        for path in config_files:
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data.get("boss"), dict) and "channels" not in data["boss"]:
                    data["boss"]["channels"] = []
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception:
                continue

    def _sync_config(self):
        boss_cfg = self.bot.config.get("boss", {})
        self.enabled = boss_cfg.get("enabled", True)
        self.join_chance = boss_cfg.get("join_chance", 100)
        self.join_all = boss_cfg.get("join_all_guilds", True)
        self.ignore_guilds = boss_cfg.get("ignore_guilds", [])
        # Đọc danh sách kênh chỉ định từ trường "channels" trên Web Dashboard (Categories -> BOSS -> Channels)
        raw_channels = boss_cfg.get("channels", boss_cfg.get("target_channels", []))
        if isinstance(raw_channels, str):
            raw_channels = [c.strip() for c in raw_channels.split(",") if c.strip()]
        self.target_channels = [
            str(c).strip() for c in (raw_channels or []) if str(c).strip()
        ]

    def _update_playing_guilds(self):
        self.playing_guild_ids.clear()
        for c_id in getattr(self.bot, "channels", []):
            try:
                ch = self.bot.get_channel(int(c_id))
                if ch and getattr(ch, "guild", None):
                    self.playing_guild_ids.add(str(ch.guild.id))
            except (ValueError, TypeError):
                continue

        if hasattr(self.bot, "guild_id") and self.bot.guild_id:
            self.playing_guild_ids.add(str(self.bot.guild_id))

    def register_actions(self):
        self._ensure_dashboard_config_schema()
        self._sync_config()
        self._update_playing_guilds()
        if self.target_channels:
            self.bot.log(
                "BOSS",
                f"Auto Boss active on designated channels: {', '.join(self.target_channels)}",
            )

    def _load_state(self):
        self.tickets = 3
        self.last_reset = 0
        self.joined_ids = set()

        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.tickets = data.get("tickets", 3)
                    self.last_reset = data.get("last_reset", 0)
                    self.joined_ids = set(data.get("joined_ids", []))
            except Exception:
                pass

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "tickets": self.tickets,
                        "last_reset": self.last_reset,
                        "joined_ids": list(self.joined_ids),
                    },
                    f,
                    indent=4,
                )
        except Exception:
            pass

    def _check_reset(self):
        now = time.time()
        if now - self.last_reset >= 72000:
            self.tickets = 3
            self.last_reset = now
            self.joined_ids.clear()
            self._save_state()

    @commands.Cog.listener()
    async def on_message(self, message):
        if str(message.author.id) != str(self.bot.owo_bot_id):
            return
        if message.channel.id != self.bot.channel_id:
            return
        if not self.bot.is_message_for_me(message):
            return

        full_content = self.bot.get_full_content(message).lower()

        if "boss ticket" in full_content:
            match = re.search(r"(\d+)/3 boss ticket", full_content)
            if match:
                self.tickets = int(match.group(1))
                self.last_reset = time.time()
                self._save_state()
                self.bot.log("BOSS", f"Synced boss tickets: {self.tickets}/3")
            elif "ran out of boss tickets" in full_content:
                self.tickets = 0
                self.last_reset = time.time()
                self._save_state()
                self.bot.log("BOSS", "Synced boss tickets: 0/3 (Out of tickets)")

    @commands.Cog.listener()
    async def on_socket_raw_receive(self, msg):
        # Đồng bộ lại cấu hình mới nhất từ bộ nhớ (khi người dùng bấm Save trên Web Dashboard)
        self._sync_config()
        if not self.enabled or self.bot.paused:
            return

        try:
            payload = json.loads(msg)
        except Exception:
            return

        if payload.get("t") != "MESSAGE_CREATE":
            return

        data = payload.get("d", {})
        if str(data.get("author", {}).get("id")) != str(self.bot.owo_bot_id):
            return

        components = parse_v2_message(data)
        if not components:
            return

        v2_text = " ".join(
            getattr(c, "content", "") or "" for c in components
        ).lower()
        msg_content = (data.get("content") or "").lower()
        combined_text = f"{msg_content} {v2_text}"

        fight_btn = next(
            (c for c in components if getattr(c, "custom_id", None) == "guildboss_fight"),
            None,
        )
        if not fight_btn and "runs away" not in combined_text and "guild boss" not in combined_text:
            return

        channel_id = int(data.get("channel_id", 0))
        guild_id = str(data.get("guild_id") or "")

        # 1. Bỏ qua nếu thuộc server bị chặn trong ignore_guilds
        if guild_id in [str(g) for g in self.ignore_guilds]:
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

        if not can_join or not fight_btn:
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
            self.bot.log("ERROR", "Failed to join Boss Battle.")


async def setup(bot):
    await bot.add_cog(Boss(bot))
