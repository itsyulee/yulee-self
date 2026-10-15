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


import aiohttp
import asyncio

class CaptchalyService:
    def __init__(self, bot, api_key, site_key):
        self.bot = bot
        self.api_key = api_key
        self.site_key = site_key

    async def get_balance(self):
        if not self.api_key:
            return 0
        url = f"https://v1.captchaly.com/account?apikey={self.api_key}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return float(data.get("balance", 0))
                    return 0
        except Exception as e:
            self.bot.log("ERROR", f"Failed to get Captchaly balance: {e}")
            return 0

    async def solve_hcaptcha(self, retries=2):
        if not self.api_key:
            self.bot.log("ERROR", "Captchaly API key missing.")
            return None

        url = f"https://v1.captchaly.com/hcaptcha?url=https://owobot.com&sitekey={self.site_key}&apikey={self.api_key}"

        async with aiohttp.ClientSession() as session:
            for attempt in range(retries):
                try:
                    self.bot.log("SYS", f"Creating Captchaly task (Attempt {attempt+1})...")
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            token = data.get("token")
                            if token:
                                self.bot.log("SUCCESS", "Captchaly solved hCaptcha successfully.")
                                return token
                            self.bot.log("ERROR", "Captchaly response missing token.")
                        elif resp.status == 429:
                            self.bot.log("ERROR", "Captchaly: Concurrency limit reached.")
                            await asyncio.sleep(5)
                        elif resp.status == 402:
                            self.bot.log("ERROR", "Captchaly: Not Enough Funds.")
                            break
                        elif resp.status == 503:
                            self.bot.log("ERROR", "Captchaly: CAPTCHA_UNSOLVABLE (timeout reached).")
                        else:
                            try:
                                data = await resp.json()
                                self.bot.log("ERROR", f"Captchaly Error {resp.status}: {data}")
                            except:
                                self.bot.log("ERROR", f"Captchaly Error {resp.status}")
                except asyncio.TimeoutError:
                    self.bot.log("ERROR", "Captchaly task timed out (120s limit).")
                except Exception as e:
                    self.bot.log("ERROR", f"Captchaly task exception: {e}")
            return None