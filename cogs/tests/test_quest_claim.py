import ast
import asyncio
import re
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from utils.quest_tracking import message_text, parse_tracking


class ClaimTests(unittest.TestCase):
    def test_claim_buttons_and_deduplication(self):
        tree = ast.parse(Path('cogs/quest.py').read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_parse_quests_v2')
        method.decorator_list = []
        ns = dict(re=re, time=time, asyncio=asyncio, message_text=message_text, parse_tracking=parse_tracking)
        exec(compile(ast.Module(body=[method], type_ignores=[]), '<claim>', 'exec'), ns)

        async def run():
            calls = []
            async def click(**kwargs):
                calls.append(kwargs)
            cog = SimpleNamespace(_claim_attempts={}, bot=SimpleNamespace(
                config={}, log=lambda *a: None, interactions=SimpleNamespace(click_button_raw=click)))
            button = lambda label, disabled=False: SimpleNamespace(
                name='button', custom_id='reward:owner', label=label, disabled=disabled)
            for index, header in enumerate(('Quest Log', 'Daily Checklist', 'Weekly Checklist')):
                data = dict(id=str(index), channel_id='5', author={'id': '999'},
                            content=f"<@123>'s {header}")
                ns['_parse_quests_v2'](cog, [button('Claim Rewards', True), button('Shop')], data)
                ns['_parse_quests_v2'](cog, [button('Claim Rewards')], data)
                ns['_parse_quests_v2'](cog, [button('Claim Rewards')], data)
            await asyncio.sleep(0)
            self.assertEqual(len(calls), 3)
            cog.bot.config = {'commands': {'quest': {'auto_claim': False}}}
            ns['_parse_quests_v2'](cog, [button('Claim')], dict(data, id='off'))
            await asyncio.sleep(0)
            self.assertEqual(len(calls), 3)
        asyncio.run(run())
