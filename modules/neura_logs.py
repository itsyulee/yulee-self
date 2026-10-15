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


import time
import json
import os
from rich.console import Console

class NeuraLogs:
    def __init__(self):
        self.console = Console()
        self.log_config = {}
        self.last_logs = {}
        self._load_config()

    def _load_config(self):
        try:
            config_path = os.path.join(os.getcwd(), 'config', 'logmisc.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.log_config = json.load(f)
                    
                    import core.state as state
                    state.log_config = self.log_config
        except:
            pass

    def log(self, bot, log_type, message):
        now = time.time()
        bot_uid = bot.user.id if (hasattr(bot, '_connection') and bot.user) else (getattr(bot, 'user_id', 'initialization'))
        dedup_key = f"{bot_uid}:{log_type}:{message}"
        if now - self.last_logs.get(dedup_key, 0) < 1.0:
            return
        self.last_logs[dedup_key] = now

        type_colors = self.log_config.get("colors", {})
        colors = {
            'SYS': 'cyan',
            'CMD': 'green',
            'INFO': 'blue',
            'SUCCESS': 'bright_green',
            'COOLDOWN': 'bright_yellow',
            'ALARM': 'bright_red',
            'ERROR': 'red',
            'SECURITY': 'red',
            'AutoHunt': 'bright_cyan',
            'STEALTH': 'yellow'
        }

        for k, v in type_colors.items():
            colors[k] = v.replace('#', '') 

        color = colors.get(log_type, "white")
        t = time.strftime("%I:%M:%S %p")
        
        username = bot.username if hasattr(bot, 'username') else "Bot"
        name_tag = f"[[magenta]{username}[/magenta]] "
        
        if log_type == "STEALTH":
            self.console.print(f"{name_tag}[dim]{t}[/dim] [[bold yellow]{log_type}[/bold yellow]]  {message}")
        else:
            if log_type in type_colors:
                rich_color = type_colors[log_type]
                self.console.print(f"\r{name_tag}[dim]{t}[/dim] [[bold {rich_color}]{log_type}[/bold {rich_color}]]  {message}")
            else:
                self.console.print(f"\r{name_tag}[dim]{t}[/dim] [[bold {color}]{log_type}[/bold {color}]]  {message}")

        import core.state as state
        bot_id = str(bot.user.id) if (hasattr(bot, '_connection') and bot.user) else (getattr(bot, 'user_id', None))
        state.log_command(log_type, message, "info", bot_name=username, bot_id=bot_id)

neura_logger = NeuraLogs()
