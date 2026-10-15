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



# you can singup by using this link to support this project 
# https://getcaptchasolution.com/nvmcytttsy 


import aiohttp
import asyncio

class AntiCaptchaService:
    def __init__(self, bot, api_key, site_key):
        self.bot = bot
        self.api_key = api_key
        self.site_key = site_key
        self.base_url = "https://api.anti-captcha.com"

    async def get_balance(self):
        if not self.api_key:
            return 0
        url = f"{self.base_url}/getBalance"
        payload = {"clientKey": self.api_key}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("errorId") == 0:
                            return float(data.get("balance", 0))
                    return 0
        except Exception as e:
            self.bot.log("ERROR", f"Failed to get Anti-Captcha balance: {e}")
            return 0

    async def solve_hcaptcha(self, retries=3):
        if not self.api_key:
            self.bot.log("ERROR", "Anti-Captcha API key missing.")
            return None

        create_url = f"{self.base_url}/createTask"
        result_url = f"{self.base_url}/getTaskResult"

        task_payload = {
            "type": "HCaptchaTaskProxyless",
            "websiteURL": "https://owobot.com",
            "websiteKey": self.site_key,
        }

        payload = {
            "clientKey": self.api_key,
            "task": task_payload,
        }

        async with aiohttp.ClientSession() as session:
            for attempt in range(retries):
                try:
                    self.bot.log("SYS", f"Creating Anti-Captcha hCaptcha task (Attempt {attempt+1})...")

                    async with session.post(create_url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        data = await resp.json()

                    if data.get("errorId") != 0:
                        error_desc = data.get('errorDescription', 'Unknown error')
                        self.bot.log("ERROR", f"Anti-Captcha Error: {error_desc}")
                        if data.get("errorId") == 16:
                            self.bot.log("ERROR", "Anti-Captcha: Insufficient balance.")
                            break
                        if data.get("errorId") in [10, 11, 12]:
                            self.bot.log("ERROR", f"Anti-Captcha: {error_desc}")
                            break
                        continue

                    task_id = data.get("taskId")
                    if not task_id:
                        self.bot.log("ERROR", "Anti-Captcha: No task ID returned.")
                        continue

                    self.bot.log("SYS", f"Anti-Captcha task created: {task_id}")

                    for _ in range(45):
                        await asyncio.sleep(2)

                        try:
                            async with session.post(result_url, json={"clientKey": self.api_key, "taskId": task_id},
                                                   timeout=aiohttp.ClientTimeout(total=10)) as res_resp:
                                res = await res_resp.json()

                            if res.get("status") == "ready":
                                solution = res.get("solution", {}).get("gRecaptchaResponse")
                                if solution:
                                    self.bot.log("SUCCESS", "Anti-Captcha solved hCaptcha successfully.")
                                    return solution
                                self.bot.log("ERROR", "Anti-Captcha: Solution missing gRecaptchaResponse.")
                                break

                            if res.get("errorId") != 0:
                                self.bot.log("ERROR", f"Anti-Captcha Error: {res.get('errorDescription', 'Unknown error')}")
                                break

                        except asyncio.TimeoutError:
                            continue

                except asyncio.TimeoutError:
                    self.bot.log("ERROR", "Anti-Captcha createTask timed out.")
                except Exception as e:
                    self.bot.log("ERROR", f"Anti-Captcha task exception: {e}")

            return None