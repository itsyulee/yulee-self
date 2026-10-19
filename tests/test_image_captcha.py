"""Isolated handler tests, following the repository's AST-based test style."""
import ast
import asyncio
from pathlib import Path
import re
from types import SimpleNamespace
import unicodedata
import unittest
from unittest.mock import AsyncMock, Mock


source = Path(__file__).resolve().parents[1] / 'cogs/security.py'
tree = ast.parse(source.read_text())
security = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Security')
methods = [n for n in security.body if getattr(n, 'name', '') in
           {'_normalize', '_image_letter_count', '_handle_image_captcha'}]
namespace = dict(re=re, unicodedata=unicodedata)
exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.ClassDef(name='Handler', bases=[], keywords=[],
     body=methods, decorator_list=[])], type_ignores=[])), str(source), 'exec'), namespace)
Handler = namespace['Handler']


class ImageCaptchaTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.cog = Handler()
        self.cog.monitor_id = '42'
        self.cog.bot = SimpleNamespace(stats={}, paused=False, throttle_until=0,
            _solving_captcha=False, log=Mock(),
            captcha_solver=SimpleNamespace(solve_image=AsyncMock(return_value='abc')))
        self.cog.play_beep = AsyncMock()
        self.cog._show_desktop_notification = Mock()
        self.author = SimpleNamespace(id=42, send=AsyncMock())
        self.message = SimpleNamespace(id=100, author=self.author,
            attachments=[SimpleNamespace(url='https://example.invalid/image.png')],
            channel=SimpleNamespace(send=AsyncMock()))
        self.text = 'Please DM me with only the following **3 letter word** to check that you are a human!'

    def test_counts(self):
        for text in (self.text, '3letterword', '3-letter word', '3 LETTER WORD'):
            self.assertEqual(self.cog._image_letter_count(text), 3)
        self.assertIsNone(self.cog._image_letter_count('unknown'))

    async def test_guild_challenge_sends_dm_and_waits_for_confirmation(self):
        await self.cog._handle_image_captcha(self.message, self.text)
        self.author.send.assert_awaited_once_with('abc')
        self.message.channel.send.assert_not_awaited()
        self.cog.bot.captcha_solver.solve_image.assert_awaited_once_with(
            'https://example.invalid/image.png', 3)
        self.assertTrue(self.cog.bot.paused)
        self.assertTrue(self.cog.bot._solving_captcha)
        await self.cog._handle_image_captcha(self.message, self.text)
        self.author.send.assert_awaited_once()

    async def test_short_prediction_is_not_sent(self):
        self.cog.bot.captcha_solver.solve_image.return_value = 'ab'
        await self.cog._handle_image_captcha(self.message, self.text)
        self.author.send.assert_not_awaited()
        self.assertTrue(self.cog.bot.paused)
        self.assertFalse(self.cog.bot._solving_captcha)

    async def test_unknown_count_does_not_guess(self):
        await self.cog._handle_image_captcha(self.message, 'captcha')
        self.cog.bot.captcha_solver.solve_image.assert_not_awaited()
        self.author.send.assert_not_awaited()

    async def test_dm_failure_keeps_paused(self):
        self.author.send.side_effect = RuntimeError('DM blocked')
        await self.cog._handle_image_captcha(self.message, self.text)
        self.assertTrue(self.cog.bot.paused)
        self.assertFalse(self.cog.bot._solving_captcha)

    async def test_model_failure_is_handled(self):
        self.cog.bot.captcha_solver.solve_image.side_effect = RuntimeError('model failed')
        await self.cog._handle_image_captcha(self.message, self.text)
        self.author.send.assert_not_awaited()
        self.assertTrue(self.cog.bot.paused)

    async def test_other_author_is_ignored(self):
        self.author.id = 99
        await self.cog._handle_image_captcha(self.message, self.text)
        self.author.send.assert_not_awaited()
        self.assertFalse(self.cog.bot.paused)


if __name__ == '__main__':
    unittest.main()
