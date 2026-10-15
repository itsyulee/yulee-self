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
import random
import time

SPEED_PRESETS = {
    "fast": {
        "reaction_min": 0.1,
        "reaction_max": 0.4,
        "key_delay_min": 0.01,
        "key_delay_max": 0.03,
        "mistake_rate": 0.0,
        "enter_delay_min": 0.2,
        "enter_delay_max": 0.4
    },
    "medium": {
        "reaction_min": 0.4,
        "reaction_max": 1.0,
        "key_delay_min": 0.02,
        "key_delay_max": 0.05,
        "mistake_rate": 0.02,
        "enter_delay_min": 0.3,
        "enter_delay_max": 0.6
    },
    "slow": {
        "reaction_min": 1.0,
        "reaction_max": 2.2,
        "key_delay_min": 0.04,
        "key_delay_max": 0.08,
        "mistake_rate": 0.05,
        "enter_delay_min": 0.5,
        "enter_delay_max": 1.0
    }
}

def normalize_time(val):
    if not isinstance(val, (int, float)):
        return 0.1
    if val < 0:
        val = 0
    return val / 1000.0 if val >= 2 else val

def normalize_mistake(val):
    if not isinstance(val, (int, float)):
        return 0.0
    if val < 0:
        val = 0
    if val > 1:
        return val / 100.0
    return val

def validate_pair(min_val, max_val):
    min_val = normalize_time(min_val)
    max_val = normalize_time(max_val)
    if min_val > max_val:
        min_val, max_val = max_val, min_val
    return min_val, max_val

class NeuraHuman:
    @staticmethod
    async def neura_send(bot, channel, content):
        if getattr(bot, 'is_on_break', False):
            bot.log("STEALTH", "Waiting for existing break to finish...")
            while getattr(bot, 'is_on_break', False):
                await asyncio.sleep(1)

        stealth_cfg = bot.config.get('stealth', {})
        hb_cfg = stealth_cfg.get('human_break', {})
        hb_enabled = hb_cfg.get('enabled', True)
        hb_duration = hb_cfg.get('duration_min', 10) * 60
        hb_interval = hb_cfg.get('interval_min', 45) * 60

        grind_active = getattr(bot, 'grind_active_time', 0.0)
        last_check = getattr(bot, 'last_break_check', 0.0)
        runtime = grind_active - last_check

        if hb_enabled and runtime > hb_interval:
            break_lock = getattr(bot, 'break_lock', None)
            if break_lock:
                async with break_lock:
                    if getattr(bot, 'grind_active_time', 0.0) - getattr(bot, 'last_break_check', 0.0) > hb_interval and not getattr(bot, 'is_on_break', False):
                        bot.is_on_break = True
                        start_break_time = time.time()
                        bot.log("STEALTH", f"Break started – pausing for {int(hb_duration/60)} min")
                        try:
                            while bot.is_on_break:
                                curr_stealth = bot.config.get('stealth', {})
                                curr_hb = curr_stealth.get('human_break', {})
                                if not curr_hb.get('enabled', True):
                                    bot.log("STEALTH", "Break interrupted – disabled in settings")
                                    break
                                curr_duration = curr_hb.get('duration_min', 10) * 60
                                if time.time() - start_break_time >= curr_duration:
                                    break
                                await asyncio.sleep(1)
                        finally:
                            bot.last_break_check = bot.grind_active_time
                            bot.is_on_break = False
                            bot.log("STEALTH", "Break finished – resuming")

        typing_enabled = stealth_cfg.get('typing_enabled', None)
        if typing_enabled is None:
            typing_cfg = stealth_cfg.get('typing', {})
            typing_enabled = typing_cfg.get('enabled', False) if isinstance(typing_cfg, dict) else False

        if not typing_enabled:
            try:
                await channel.send(content)
                return True
            except Exception:
                return False

        speed_preset_name = stealth_cfg.get('speed_preset', 'medium')
        custom_overrides = stealth_cfg.get('speed_custom', {})
        use_custom = custom_overrides.get('enabled', False) if isinstance(custom_overrides, dict) else False

        preset = SPEED_PRESETS.get(speed_preset_name, SPEED_PRESETS["medium"]).copy()
        if use_custom:
            for key in preset:
                if key in custom_overrides and isinstance(custom_overrides[key], (int, float)):
                    preset[key] = custom_overrides[key]

        reaction_min, reaction_max = validate_pair(preset["reaction_min"], preset["reaction_max"])
        key_delay_min, key_delay_max = validate_pair(preset["key_delay_min"], preset["key_delay_max"])
        enter_delay_min, enter_delay_max = validate_pair(preset["enter_delay_min"], preset["enter_delay_max"])

        log_str = f"Settings: preset={speed_preset_name}, custom={use_custom}, reaction {reaction_min:.2f}–{reaction_max:.2f}s, key {key_delay_min:.2f}–{key_delay_max:.2f}s, enter {enter_delay_min:.2f}–{enter_delay_max:.2f}s"
        if getattr(bot, 'last_stealth_log', None) != log_str:
            bot.log("STEALTH", log_str)
            bot.last_stealth_log = log_str

        reaction_time = random.uniform(reaction_min, reaction_max)
        if reaction_time > 0.1:
            await asyncio.sleep(reaction_time)

        try:
            async with channel.typing():
                chars = list(str(content))
                i = 0
                typing_start = time.time()

                while i < len(chars):
                    if bot.paused:
                        return False
                    char = chars[i]
                    delay = random.uniform(key_delay_min, key_delay_max)
                    if char in ".,!?;":
                        delay += random.uniform(0.1, 0.2)

                    await asyncio.sleep(delay)
                    i += 1

                enter_delay = random.uniform(enter_delay_min, enter_delay_max)
                await asyncio.sleep(enter_delay)

                total_time = round(time.time() - typing_start, 2)
                bot.last_typing_time = total_time

                await channel.send(content)
                return True

        except Exception:
            try:
                await channel.send(content)
                return True
            except Exception as final_e:
                bot.log("ERROR", f"Critical send failure: {final_e}")
                return False

    @staticmethod
    def neura_calculate_typing_speed(text, wpm=55):
        return (len(text) / 5) / wpm * 60