import asyncio
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import orbit


class OrbitTests(unittest.TestCase):
    def test_read_request_retries_transient_failure(self):
        good = io.BytesIO(json.dumps({'tweets': [{'id': '123'}]}).encode())
        with patch.dict(os.environ, {'TWITTERAPI_KEY': 'test'}), \
             patch.object(orbit.urllib.request, 'urlopen', side_effect=[urllib.error.URLError('network'), good]) as request, \
             patch.object(orbit.time, 'sleep') as sleep:
            self.assertIn('123', orbit.fetch_tweets(['123']))
            self.assertEqual(request.call_count, 2)
            sleep.assert_called_once_with(5)

    def test_start_date_skips_today_and_allows_tomorrow(self):
        with patch.dict(os.environ, {'ORBIT_NOT_BEFORE': '2026-11-02'}):
            self.assertTrue(orbit.before_start_date(datetime(2026, 11, 1, 11, 5, tzinfo=orbit.IST)))
            self.assertFalse(orbit.before_start_date(datetime(2026, 11, 2, 7, 0, tzinfo=orbit.IST)))

    def test_slot_boundaries(self):
        for mode, hour, minute in [('mega-post', 11, 5), ('mega-engage', 11, 35),
                                   ('likes', 7, 0), ('likes', 12, 0), ('likes', 13, 0),
                                   ('likes', 17, 0), ('likes', 22, 0)]:
            orbit.confirm_slot(mode, datetime(2026, 11, 1, hour, minute, tzinfo=orbit.IST))
        with self.assertRaises(RuntimeError):
            orbit.confirm_slot('mega-post', datetime(2026, 11, 1, 10, 59, tzinfo=orbit.IST))
        with self.assertRaises(RuntimeError):
            orbit.confirm_slot('mega-engage', datetime(2026, 11, 1, 11, 30, tzinfo=orbit.IST))
        orbit.confirm_slot('mega-engage', datetime(2026, 11, 1, 14, 20, tzinfo=orbit.IST))
        with self.assertRaises(RuntimeError):
            orbit.confirm_slot('mega-engage', datetime(2026, 11, 1, 14, 25, tzinfo=orbit.IST))
        self.assertEqual(orbit.like_slot(datetime(2026, 11, 1, 12, 59, tzinfo=orbit.IST)), 'likes-12')
        self.assertEqual(orbit.like_slot(datetime(2026, 11, 1, 13, 10, tzinfo=orbit.IST)), 'likes-13')
        with self.assertRaises(RuntimeError):
            orbit.like_slot(datetime(2026, 11, 1, 15, 0, tzinfo=orbit.IST))

    def test_overlapping_like_slots_keep_unfinished_noon_cycle(self):
        when = datetime(2026, 11, 1, 13, 10, tzinfo=orbit.IST)
        self.assertEqual(orbit.due_like_slots(when, {}), ['likes-12', 'likes-13'])
        state = {'2026-11-01:likes-12:complete': 'done'}
        self.assertEqual(orbit.due_like_slots(when, state), ['likes-13'])

    def test_one_day_post_override_and_extra_sessions_expire(self):
        config = {'date': '2026-11-02',
                  'url': 'https://x.com/SinClair_0000/status/2117164586495615402',
                  'extra_mega_hour': 16,
                  'scroll_retry_minutes': 240,
                  'extra_scroll_times': ['14:30', '16:00', '18:00', '20:00']}
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(orbit, 'SPECIAL', Path(temp) / 'special.json'):
            orbit.SPECIAL.write_text(json.dumps(config))
            afternoon = datetime(2026, 11, 2, 14, 30, tzinfo=orbit.IST)
            self.assertEqual(orbit.scroll_post(afternoon, 'likes-1430'),
                             ('2026-11-02', config['url']))
            self.assertIn('likes-1430', orbit.due_like_slots(afternoon, {}))
            self.assertIn('likes-12', orbit.due_like_slots(afternoon, {}))
            self.assertEqual(orbit.due_like_slots(datetime(2026, 11, 2, 17, 0,
                             tzinfo=orbit.IST), {}),
                             ['likes-1430', 'likes-1600', 'likes-17'])
            self.assertEqual(orbit.mega_session(datetime(2026, 11, 2, 16, 5,
                             tzinfo=orbit.IST)), ('mega-16', 16))
            orbit.confirm_slot('mega-post', datetime(2026, 11, 2, 16, 5,
                               tzinfo=orbit.IST))
            orbit.confirm_slot('mega-engage', datetime(2026, 11, 2, 16, 35,
                               tzinfo=orbit.IST))
            tomorrow = datetime(2026, 11, 3, 14, 30, tzinfo=orbit.IST)
            self.assertNotIn('likes-1430', orbit.due_like_slots(tomorrow, {}))
            self.assertEqual(orbit.mega_session(datetime(2026, 11, 3, 16, 5,
                             tzinfo=orbit.IST)), ('mega', 11))

    def test_hourly_scroll_uses_ten_new_links_after_latest_own_share(self):
        def msg(mid, author, tweet_id, out=False):
            return SimpleNamespace(id=mid, out=out,
                                   message=f'https://x.com/{author}/status/{tweet_id}')
        messages = [msg(3, 'SinClair_0000', '999', True),
                    msg(1, 'SinClair_0000', '999', True),
                    msg(2, 'a', '100'),
                    *[msg(i, f'user{i}', str(200 + i)) for i in range(4, 15)],
                    msg(15, 'SinClair_0000', '999')]
        anchor, links = orbit.links_after_own_share(list(reversed(messages)),
            'https://x.com/SinClair_0000/status/999', 'SinClair_0000')
        self.assertEqual(anchor, 3)
        self.assertEqual([x['message_id'] for x in links], list(range(14, 4, -1)))
        self.assertEqual(len(links), 10)
        newer = messages + [msg(16, 'later', '9999')]
        self.assertEqual([x['message_id'] for x in orbit.latest_links_since_anchor(newer, 3, 'SinClair_0000')],
                         [16] + list(range(14, 5, -1)))

    def test_backlogged_scroll_uses_new_link_guard_before_sharing_again(self):
        url = 'https://x.com/SinClair_0000/status/999'
        own = SimpleNamespace(id=42, out=True, message=url)
        when = datetime(2026, 11, 2, 14, 30, tzinfo=orbit.IST)
        with patch.object(orbit, 'group_and_topic', new_callable=AsyncMock,
                          return_value=('chat', SimpleNamespace(id=1))), \
             patch.object(orbit, 'messages_in_topic', new_callable=AsyncMock,
                          return_value=[own]), \
             patch.object(orbit, 'scroll_post', return_value=('2026-11-02', url)), \
             patch.object(orbit, 'execute_hourly_scroll', new_callable=AsyncMock) as guarded:
            asyncio.run(orbit.execute(None, 'likes', when, False, slot_override='likes-1430'))
            guarded.assert_awaited_once_with(None, when, False, slot_override='likes-1430')

    def test_seven_am_repeated_share_uses_yesterdays_tweet(self):
        url = 'https://x.com/SinClair_0000/status/999'
        when = datetime(2026, 11, 4, 7, 0, tzinfo=orbit.IST)
        own = SimpleNamespace(id=42, out=True, message=url,
                              date=datetime(2026, 11, 3, 22, 0, tzinfo=orbit.IST))
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(orbit, 'OUT', Path(temp)), \
             patch.object(orbit, 'load_state', return_value={}), \
             patch.object(orbit, 'scroll_post', return_value=('2026-11-03', url)), \
             patch.object(orbit, 'group_and_topic', new_callable=AsyncMock,
                          return_value=('chat', SimpleNamespace(id=1, closed=False))), \
             patch.object(orbit, 'messages_in_topic', new_callable=AsyncMock,
                          return_value=[own]):
            asyncio.run(orbit.execute_hourly_scroll(None, when, False,
                                                    slot_override='likes-07'))

    def test_regular_scroll_recheck_replaces_oldest_link_when_new_one_arrives(self):
        def msg(mid, author):
            return SimpleNamespace(id=mid, message=f'https://x.com/{author}/status/{mid}')
        first = [msg(i, f'user{i}') for i in range(1, 11)]
        self.assertEqual([x['message_id'] for x in orbit.latest_scroll_links(first, 'SinClair_0000')],
                         list(range(10, 0, -1)))
        with_new = first + [msg(11, 'SinClair_0000'), msg(12, 'new_member')]
        self.assertEqual([x['message_id'] for x in orbit.latest_scroll_links(with_new, 'SinClair_0000')],
                         [12] + list(range(10, 1, -1)))

    def test_hourly_scroll_expires_after_configured_date(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(orbit, 'HOURLY_SCROLL', Path(temp) / 'hourly.json'):
            orbit.HOURLY_SCROLL.write_text(json.dumps({'date': '2026-11-01',
                                                        'hours': [19, 20, 21, 22, 23]}))
            self.assertEqual(orbit.hourly_scroll_slot(datetime(2026, 11, 1, 19, 0, tzinfo=orbit.IST)), 'scroll-19')
            self.assertEqual(orbit.hourly_scroll_slot(datetime(2026, 11, 1, 22, 0, tzinfo=orbit.IST)), 'likes-22')
            self.assertIsNone(orbit.hourly_scroll_slot(datetime(2026, 11, 2, 19, 0, tzinfo=orbit.IST)))
            self.assertEqual(orbit.due_hourly_scroll_slots(datetime(2026, 11, 1, 20, 0, tzinfo=orbit.IST), {}),
                             ['scroll-19', 'scroll-20'])
            self.assertEqual(orbit.due_hourly_scroll_slots(datetime(2026, 11, 1, 20, 0, tzinfo=orbit.IST),
                             {'2026-11-01:scroll-19:complete': 'done'}), ['scroll-20'])

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

    def test_pending_like_retries_after_proxy_timeout(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(orbit, 'STATE', Path(temp) / 'state.json'), \
             patch.object(orbit, 'x_action', side_effect=[RuntimeError('Proxy connection timed out'), None]) as action, \
             patch.object(orbit.time, 'sleep') as sleep:
            key = '2026-11-01:mega:123:like'
            state = {key: 'pending'}
            orbit.ensure_like(state, key, '123')
            self.assertEqual(state[key], 'done')
            self.assertEqual(action.call_count, 2)
            sleep.assert_called_once_with(15)

    def test_restricted_reply_is_recorded_without_repeating_it(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(orbit, 'STATE', Path(temp) / 'state.json'), \
             patch.object(orbit, 'x_action', side_effect=orbit.ReplyRestrictedError('restricted')) as action:
            state = {}
            orbit.ensure_reply(state, '2026-11-01:mega:123:reply', '123', 'a relevant reply')
            self.assertEqual(state['2026-11-01:mega:123:reply'], 'unavailable')
            orbit.ensure_reply(state, '2026-11-01:mega:123:reply', '123', 'a relevant reply')
            action.assert_called_once()

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
