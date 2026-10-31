import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import orbit


class OrbitTests(unittest.TestCase):
    def test_slot_boundaries(self):
        for mode, hour, minute in [('mega-post', 11, 5), ('mega-engage', 11, 35),
                                   ('likes', 7, 0), ('likes', 12, 0),
                                   ('likes', 17, 0), ('likes', 22, 0)]:
            orbit.confirm_slot(mode, datetime(2026, 11, 1, hour, minute, tzinfo=orbit.IST))
        with self.assertRaises(RuntimeError):
            orbit.confirm_slot('mega-post', datetime(2026, 11, 1, 10, 59, tzinfo=orbit.IST))
        with self.assertRaises(RuntimeError):
            orbit.confirm_slot('mega-engage', datetime(2026, 11, 1, 11, 30, tzinfo=orbit.IST))
        self.assertEqual(orbit.like_slot(datetime(2026, 11, 1, 13, 10, tzinfo=orbit.IST)), 'likes-12')
        with self.assertRaises(RuntimeError):
            orbit.like_slot(datetime(2026, 11, 1, 14, 0, tzinfo=orbit.IST))

    def test_morning_mega_uses_same_day_post(self):
        history = {'2026-10-31': {'post_tweet_id': '123'},
                   '2026-11-01': {'post_tweet_id': '456'}}
        with patch.object(orbit.run_daily, 'read_state', return_value=history):
            day, url = orbit.posted_tweet_before(datetime(2026, 11, 1, 7, 0, tzinfo=orbit.IST))
            self.assertEqual(day, '2026-10-31')
            self.assertTrue(url.endswith('/123'))
            day, url = orbit.posted_tweet_before(datetime(2026, 11, 1, 11, 5, tzinfo=orbit.IST))
            self.assertEqual(day, '2026-11-01')
            self.assertTrue(url.endswith('/456'))

    def test_candidate_window_and_clean_links(self):
        def msg(id, text, minute):
            return SimpleNamespace(id=id, message=text,
                                   date=datetime(2026, 11, 1, 5, minute, tzinfo=timezone.utc))
        messages = [msg(1, 'https://x.com/A/status/123?a=tracking', 2),
                    msg(2, 'https://x.com/B/status/456', 40),
                    msg(3, 'https://x.com/A/status/123', 4)]
        links = orbit.tweet_links(messages, after=datetime(2026, 11, 1, 5, 0, tzinfo=timezone.utc),
                                  before=datetime(2026, 11, 1, 5, 35, tzinfo=timezone.utc))
        self.assertEqual([x['id'] for x in links], ['123'])
        self.assertEqual(links[0]['url'], 'https://x.com/A/status/123')

    def test_interrupted_external_action_is_not_repeated(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(orbit, 'STATE', Path(temp) / 'state.json'):
            state = {}
            calls = []
            with self.assertRaises(ValueError):
                orbit.unique_action(state, 'one', lambda: (calls.append(1), (_ for _ in ()).throw(ValueError())))
            self.assertEqual(json.loads(orbit.STATE.read_text())['one'], 'pending')
            with self.assertRaises(RuntimeError):
                orbit.unique_action(state, 'one', lambda: calls.append(2))
            self.assertEqual(calls, [1])

    def test_like_shared_across_jobs(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(orbit, 'STATE', Path(temp) / 'state.json'), \
             patch.object(orbit, 'x_action') as action:
            state = {'2026-11-01:likes-07:123:like': 'done'}
            orbit.ensure_like(state, '2026-11-01:mega:123:like', '123')
            action.assert_not_called()
            self.assertEqual(state['2026-11-01:mega:123:like'], 'done')

    def test_generic_mega_reply_is_rejected_before_engagement(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(orbit, 'OUT', Path(temp)):
            folder = Path(temp) / 'orbit' / '2026-11-01'
            folder.mkdir(parents=True)
            source = {'id': '123', 'url': 'https://x.com/a/status/123', 'author': 'a',
                      'text': 'Meteora liquidity rose today'}
            (folder / 'candidates.json').write_text(json.dumps([source]))
            (folder / 'replies.json').write_text(json.dumps([{**source, 'reply': 'Great post, thanks for sharing'}]))
            with self.assertRaises(RuntimeError):
                orbit.draft_replies([{'id': '123', 'url': source['url']}], '2026-11-01', False)


if __name__ == '__main__':
    unittest.main()
