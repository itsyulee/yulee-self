import unittest
import ast
import asyncio
import json
import time
from pathlib import Path
from types import SimpleNamespace
from utils.quest_tracking import message_text, parse_tracking, belongs_to_user, tracking_images


class QuestTrackingTests(unittest.TestCase):
    def test_finished_without_rows(self):
        kind, rows, timer = parse_tracking(
            "### <@123>'s Quest Log\nUwU You finished all of your quests! "
            "Come back tomorrow! <3\n-# ⏰ Next quest: ****")
        self.assertEqual(kind, 'quest')
        self.assertTrue(rows[0]['completed'])
        self.assertEqual(rows[0]['current'], rows[0]['total'])

    def test_unknown_layout_is_not_completion(self):
        self.assertEqual(parse_tracking("Quest Log\nLoading...")[1], [])

    def test_quest_title_is_description(self):
        kind, rows, timer = parse_tracking("<@123>'s Quest Log\nComplete quests to earn rewards!\nBalance: 85 Quest Seals\n**1. 🙏 Receive prayers**\n0/3\nCompletion rewards\n+100 +10\nNext quest: <t:1800000000:R>")
        self.assertEqual(kind, 'quest')
        self.assertEqual(rows, [dict(description='Receive prayers', current=0, total=3, completed=False)])
        self.assertEqual(timer, {'timestamp': 1800000000})

    def test_daily_rows_and_summary(self):
        text = "<@123>'s Daily Checklist\nComplete 6 tasks to earn your daily reward!\n"
        names = ['Claim your daily', 'Claim a vote', 'Send a cookie', 'Claim a quest', 'Use 3 Boss Tickets', 'Find 3 Lootboxes', 'Find 3 Weapon Crates']
        values = ['1/1','1/1','0/1','1/1','1/3','3/3','3/3']
        text += '\n'.join(f'**~~{name}~~**\n{value}' for name, value in zip(names, values))
        text += '\nDaily Progress\n5/6\nDaily checklist resets <t:1800000000:R>'
        kind, rows, _ = parse_tracking(text)
        self.assertEqual(kind, 'daily')
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[4]['description'], 'Use 3 Boss Tickets')
        self.assertFalse(rows[4]['completed'])

    def test_weekly_inline_progress(self):
        text = "<@123>'s Weekly Checklist\nRewards already claimed\n"
        text += '\n'.join(['~~Hunt 100 times~~ 100/100', 'Battle 100 times 100/100', 'Claim 5 votes 5/5', 'Send 4 cookies 4/4', 'Use 5 Boss Tickets 5/5'])
        text += '\nYou claimed your rewards!\n3 3 10K\nWeekly checklist resets <t:1800000000:R>'
        kind, rows, _ = parse_tracking(text)
        self.assertEqual(kind, 'weekly')
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(row['completed'] for row in rows))

    def test_nested_components_once_and_buttons_ignored(self):
        data = {'components': [{'type': 17, 'components': [{'type': 9, 'components': [{'type': 10, 'content': "<@123>'s Quest Log\n1. Receive prayers\n0 / 3"}], 'accessory': {'type': 2, 'label': 'Weekly Checklist'}}]}]}
        self.assertEqual(len(parse_tracking(message_text(data))[1]), 1)
        self.assertEqual(parse_tracking(message_text(data))[0], 'quest')

    def test_owner_requires_header(self):
        self.assertTrue(belongs_to_user("<@123>'s Quest Log", 123, []))
        self.assertFalse(belongs_to_user("<@456>'s Quest Log\n<@123>", 123, ['']))
        self.assertFalse(belongs_to_user("<@456>'s Quest Log", 123, ['Quest']))
        self.assertTrue(belongs_to_user("**@breakin' heart's Quest Log**", 123, ["breakin' heart"]))

    def test_legacy(self):
        _, rows, _ = parse_tracking("My Quest Log\n1. Manually hunt 10 times! Reward: 100\nProgress: [2/10]")
        self.assertEqual(rows[0]['description'], 'Manually hunt 10 times!')
        self.assertEqual(rows[0]['current'], 2)


class TrackingIntegrationTests(unittest.TestCase):
    def test_partial_updates_and_separate_accounts_and_groups(self):
        # Execute the real listener/sync methods with an inert bot: no Discord login.
        tree = ast.parse(Path('cogs/quest.py').read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        cls.body = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in ('on_socket_raw_receive', '_sync_tracking')]
        cls.bases = []
        for method in cls.body:
            method.decorator_list = []
        namespace = dict(time=time, tracking_images=tracking_images, json=json, message_text=message_text, parse_tracking=parse_tracking, belongs_to_user=belongs_to_user, parse_v2_message=lambda data: [])
        exec(compile(ast.Module(body=[cls], type_ignores=[]), '<quest listener>', 'exec'), namespace)
        cog = namespace['Quest']()
        cog.active = True
        cog._tracking_messages = {}
        cog._parse_quests_v2 = lambda *args: None
        cog.bot = SimpleNamespace(paused=False, owo_bot_id='999', channels=[5], user=SimpleNamespace(id=123, name='owner'), display_name='Owner', identifiers=[], stats={}, log=lambda *args: None)
        def event(event_type, **data):
            asyncio.run(cog.on_socket_raw_receive(json.dumps(dict(t=event_type, d=data))))
        def components(header, value):
            return [{'type': 17, 'components': [{'type': 10, 'content': f"<@123>'s {header}\n1. Receive prayers\n{value}"}]}]
        event('MESSAGE_CREATE', id='1', channel_id='5', author={'id':'999'}, components=components('Quest Log', '0/3'))
        cog.bot.paused = True
        event('MESSAGE_UPDATE', id='1', components=components('Quest Log', '2/3'))
        self.assertEqual(cog.bot.stats['quest_data'][0]['current'], 2)
        event('MESSAGE_UPDATE', id='1', components=components('Daily Checklist', '1/3'))
        event('MESSAGE_UPDATE', id='1', components=components('Weekly Checklist', '3/3'))
        self.assertEqual(cog.bot.stats['quest_data'][0]['current'], 2)
        self.assertEqual(cog.bot.stats['daily_checklist_data'][0]['current'], 1)
        self.assertEqual(cog.bot.stats['weekly_checklist_data'][0]['current'], 3)
        event('MESSAGE_CREATE', id='2', channel_id='5', author={'id':'999'}, content="<@456>'s Quest Log\n1. Receive prayers\n0/3")
        self.assertEqual(cog.bot.stats['quest_data'][0]['current'], 2)
        claims = []
        cog.bot.paused = False
        cog._parse_quests_v2 = lambda *args: claims.append(args)
        event('MESSAGE_CREATE', id='3', channel_id='6', author={'id':'999'}, components=components('Quest Log', '3/3'))
        self.assertEqual(cog.bot.stats['quest_data'][0]['current'], 2)
        self.assertEqual(claims, [])
        event('MESSAGE_UPDATE', id='3', components=components('Quest Log', '1/3'))
        self.assertEqual(cog.bot.stats['quest_data'][0]['current'], 2)
        self.assertEqual(claims, [])
        event('MESSAGE_CREATE', id='4', channel_id='5', author={'id':'999'}, components=components('Quest Log', '3/3'))
        self.assertEqual(len(claims), 1)
        event('MESSAGE_UPDATE', id='4', components=components(
            'Quest Log', 'UwU You finished all of your quests! Come back tomorrow! <3'))
        self.assertTrue(all(q['completed'] for q in cog.bot.stats['quest_data']))
        claims.clear()
        logs = []
        cog.bot.log = lambda *args: logs.append(args)
        cog.bot.stats['quest_images'] = {'quest': {'urls': ['old.png']}}
        cog.bot.stats['force_lucky_gems'] = True
        cog._sync_tracking("\n### 📜 <@711837366553411634>'s Quest Log\n"
                           "-# Complete quests to earn rewards!\n"
                           "-# Balance: **180** <:seal:1508740094125932614> Quest Seals\n"
                           "UwU You finished all of your quests! Come back tomorrow! <3\n"
                           "-# ⏰ Next quest: ****")
        self.assertTrue(cog.bot.stats['quest_data'][0]['completed'])
        self.assertNotIn('quest', cog.bot.stats['quest_images'])
        self.assertFalse(cog.bot.stats['force_lucky_gems'])
        self.assertIsNone(cog.bot.stats['next_quest_timer'])
        self.assertFalse(any(level == 'WARN' for level, _ in logs))

        def gallery(owner, filename):
            return [{'type':17, 'components':[
                {'type':10, 'content':f"### <@{owner}>'s Quest Log"},
                {'type':12, 'items':[{'media':{'url':f'https://media.discordapp.net/attachments/1/2/{filename}.png'}}]}
            ]}]
        event('MESSAGE_CREATE', id='5', channel_id='5', author={'id':'999'}, components=gallery(456, 'other'))
        self.assertNotIn('quest', cog.bot.stats['quest_images'])
        event('MESSAGE_CREATE', id='6', channel_id='6', author={'id':'999'}, components=gallery(123, 'outside'))
        self.assertNotIn('quest', cog.bot.stats['quest_images'])
        event('MESSAGE_CREATE', id='7', channel_id='5', author={'id':'999'}, components=gallery(123, 'first'))
        self.assertEqual(cog.bot.stats['quest_data'], [])
        self.assertTrue(cog.bot.stats['quest_images']['quest']['urls'][0].endswith('first.png'))
        event('MESSAGE_UPDATE', id='7', components=gallery(123, 'second'))
        self.assertTrue(cog.bot.stats['quest_images']['quest']['urls'][0].endswith('second.png'))
        self.assertEqual(len(claims), 0)

        # OwO replaces the gallery with a text-only response: discard old media.
        logs.clear()
        event('MESSAGE_UPDATE', id='7', components=[
            {'type': 10, 'content': "<@123>'s Quest Log\nNo tasks available"}
        ])
        self.assertNotIn('quest', cog.bot.stats['quest_images'])
        self.assertEqual(cog.bot.stats['quest_data'], [])
        self.assertFalse(any(level == 'WARN' for level, _ in logs))

        # Metadata-only updates must retain a gallery still on the message.
        event('MESSAGE_CREATE', id='8', channel_id='5', author={'id':'999'},
              components=gallery(123, 'retained'))
        event('MESSAGE_UPDATE', id='8', edited_timestamp='2026-10-16T10:00:00Z')
        self.assertTrue(cog.bot.stats['quest_images']['quest']['urls'][0].endswith('retained.png'))
        event('MESSAGE_UPDATE', id='8', components=[
            {'type': 10, 'content': "<@123>'s Quest Log\nUwU You finished all of your quests! Come back tomorrow! <3"}
        ])
        self.assertNotIn('quest', cog.bot.stats['quest_images'])
        self.assertTrue(cog.bot.stats['quest_data'][0]['completed'])


if __name__ == '__main__':
    unittest.main()
