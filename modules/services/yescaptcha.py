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



""" you can singup and on contacting support of yescaptcha you will get 
free 1500 credits for new singup and you can solve 50 captchas with that"""

# https://yescaptcha.com/i/hpJNaV


import aiohttp
import asyncio

class YesCaptchaService:
    def __init__(self, bot, api_key, site_key):
        self.bot = bot
        self.api_key = api_key
        self.site_key = site_key

    async def get_balance(self):
        if not self.api_key: return 0
        url = "https://api.yescaptcha.com/getBalance"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={"clientKey": self.api_key}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
                    return int(data.get("balance", 0)) if data.get("errorId") == 0 else 0
        except Exception as e:
            self.bot.log("ERROR", f"Failed to get YesCaptcha balance: {e}")
            return 0

    async def solve_hcaptcha(self, retries=2):
        """solves hcaptcha using yescaptcha api and returns the token"""
        create_url = "https://api.yescaptcha.com/createTask"
        result_url = "https://api.yescaptcha.com/getTaskResult"
        
        payload = {
            "clientKey": self.api_key,
            "task": {
                "type": "HCaptchaTaskProxyless",
                "websiteKey": self.site_key,
                "websiteURL": "https://owobot.com",
            },
            "softID": 100629,
        }

        async with aiohttp.ClientSession() as session:
            for attempt in range(retries):
                try:
                    self.bot.log("SYS", f"Creating YesCaptcha task (Attempt {attempt+1})...")
                    async with session.post(create_url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        data = await resp.json()
                    
                    if data.get("errorId") != 0:
                        self.bot.log("ERROR", f"YesCaptcha Error: {data.get('errorDescription')}")
                        continue

                    task_id = data.get("taskId")
                    for _ in range(45): 
                        await asyncio.sleep(2)
                        try:
                            async with session.post(result_url, json={"clientKey": self.api_key, "taskId": task_id}, timeout=aiohttp.ClientTimeout(total=10)) as res_resp:
                                res = await res_resp.json()
                            
                            if res.get("status") == "ready":
                                solution = res["solution"]["gRecaptchaResponse"]
                                if solution:
                                    self.bot.log("SUCCESS", "YesCaptcha solved hCaptcha successfully.")
                                    return solution
                            if res.get("errorId") != 0: 
                                self.bot.log("ERROR", f"YesCaptcha Error: {res.get('errorDescription')}")
                                break
                        except asyncio.TimeoutError:
                            continue 
                            
                except asyncio.TimeoutError:
                    self.bot.log("ERROR", "YesCaptcha createTask timed out.")
                except Exception as e:
                    self.bot.log("ERROR", f"Solver task failed: {e}")
            return None
