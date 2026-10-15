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



COMP_TYPES = {
    1: "action_row",
    2: "button",
    3: "select_menu",
    4: "text_input",
    5: "user_select",
    6: "role_select",
    7: "mentionable_select",
    8: "channel_select",
    9: "section",
    10: "text_display",
    11: "thumbnail",
    12: "media_gallery",
    13: "file",
    14: "separator",
    17: "container",
    18: "label"
}

class V2Component:
    def __init__(self, data):
        self.raw = data
        self.type = data.get("type")
        self.name = COMP_TYPES.get(self.type, "unknown")
        self.id = data.get("id")
        self.custom_id = data.get("custom_id")
        self.content = data.get("content", "")
        self.label = data.get("label", "")
        self.url = data.get("url")
        self.disabled = data.get("disabled", False)
        
        self.emoji = data.get("emoji")
        
        self.media = []
        if self.name == "media_gallery":
            for item in data.get("items", []):
                media_data = item.get("media", {})
                self.media.append({
                    "url": media_data.get("url"),
                    "proxy_url": media_data.get("proxy_url"),
                    "placeholder": media_data.get("placeholder")
                })

def walker(components_data):
    flat_list = []
    
    if not components_data:
        return flat_list

    if isinstance(components_data, dict):
        components_data = [components_data]

    for data in components_data:
        comp = V2Component(data)
        flat_list.append(comp)

        if "components" in data:
            flat_list.extend(walker(data["components"]))

        if "accessory" in data:
            flat_list.extend(walker(data["accessory"]))

    return flat_list

def parse_v2_message(msg_data):

    if not msg_data or "components" not in msg_data:
        return []
    
    return walker(msg_data["components"])

def get_boss_battle_id(components):
    for comp in components:
        if comp.name == "media_gallery" and comp.media:
            placeholder = comp.media[0].get("placeholder")
            if placeholder and "reward" in (comp.media[0].get("url") or ""):
                return placeholder
    return None
