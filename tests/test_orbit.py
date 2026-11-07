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

    def test_five_hour_scroll_and_eight_pm_mega_boundaries(self):
        history = {'2026-11-01': {'post_tweet_id': '456',
                   'posted_at': '2026-11-01T13:15:00+05:30'}}
        with patch.object(orbit.run_daily, 'read_state', return_value=history):
            for hour, minute in [(13, 15), (18, 14)]:
                orbit.confirm_slot('likes', datetime(2026, 11, 1, hour, minute, tzinfo=orbit.IST))
            for hour, minute in [(13, 14), (18, 15), (7, 0)]:
                with self.assertRaises(RuntimeError):
                    orbit.confirm_slot('likes', datetime(2026, 11, 1, hour, minute, tzinfo=orbit.IST))
        orbit.confirm_slot('mega-post', datetime(2026, 11, 1, 20, 5, tzinfo=orbit.IST))
        orbit.confirm_slot('mega-engage', datetime(2026, 11, 1, 20, 35, tzinfo=orbit.IST))
        with self.assertRaises(RuntimeError):
            orbit.confirm_slot('mega-post', datetime(2026, 11, 1, 20, 30, tzinfo=orbit.IST))
        with self.assertRaises(RuntimeError):
            orbit.confirm_slot('mega-engage', datetime(2026, 11, 1, 20, 30, tzinfo=orbit.IST))

    def test_post_window_requires_success_timestamp(self):
        when = datetime(2026, 11, 1, 13, 0, tzinfo=orbit.IST)
        with patch.object(orbit.run_daily, 'read_state', return_value={'2026-11-01': {'post_tweet_id': '456'}}):
            self.assertIsNone(orbit.post_scroll_window(when))

    def test_one_day_extra_mega_session_expires(self):
        config = {'date': '2026-11-02',
                  'url': 'https://x.com/SinClair_0000/status/2117164586495615402',
                  'extra_mega_hour': 16}
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(orbit, 'SPECIAL', Path(temp) / 'special.json'):
            orbit.SPECIAL.write_text(json.dumps(config))
            self.assertEqual(orbit.mega_session(datetime(2026, 11, 2, 16, 5,
                             tzinfo=orbit.IST)), ('mega-16', 16))
            self.assertEqual(orbit.mega_session(datetime(2026, 11, 3, 16, 5,
                             tzinfo=orbit.IST)), ('mega-20', 20))

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

    def test_rolling_scroll_uses_latest_share_as_next_anchor(self):
        url = 'https://x.com/SinClair_0000/status/999'
        own = SimpleNamespace(id=42, out=True, message=url)
        when = datetime(2026, 11, 2, 14, 30, tzinfo=orbit.IST)
        with patch.object(orbit, 'group_and_topic', new_callable=AsyncMock,
                          return_value=('chat', SimpleNamespace(id=1))), \
             patch.object(orbit, 'messages_in_topic', new_callable=AsyncMock,
                          return_value=[own]), \
             patch.object(orbit, 'post_scroll_window', return_value=(
                 datetime(2026, 11, 2, 13, 0, tzinfo=orbit.IST),
                 datetime(2026, 11, 2, 18, 0, tzinfo=orbit.IST), url)), \
             patch.object(orbit, 'execute_hourly_scroll', new_callable=AsyncMock) as guarded:
            asyncio.run(orbit.execute_post_scroll(None, when, False))
            guarded.assert_awaited_once_with(None, when, False,
                slot_override='after-42', window_end=datetime(2026, 11, 2, 18, 0,
                                                              tzinfo=orbit.IST))

    def test_rolling_scroll_waits_for_ten_new_links(self):
        url = 'https://x.com/SinClair_0000/status/999'
        when = datetime(2026, 11, 4, 14, 0, tzinfo=orbit.IST)
        own = SimpleNamespace(id=42, out=True, message=url,
                              date=datetime(2026, 11, 4, 13, 30, tzinfo=orbit.IST))
        links = [SimpleNamespace(id=i, out=False,
                 message=f'https://x.com/user{i}/status/{100+i}') for i in range(43, 52)]
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(orbit, 'OUT', Path(temp)), \
             patch.object(orbit, 'load_state', return_value={}), \
             patch.object(orbit, 'post_scroll_window', return_value=(
                 datetime(2026, 11, 4, 13, 0, tzinfo=orbit.IST),
                 datetime(2026, 11, 4, 18, 0, tzinfo=orbit.IST), url)), \
             patch.object(orbit, 'group_and_topic', new_callable=AsyncMock,
                          return_value=('chat', SimpleNamespace(id=1, closed=False))), \
             patch.object(orbit, 'messages_in_topic', new_callable=AsyncMock,
                          return_value=[own] + links), \
             patch.object(orbit, 'ensure_like') as like:
            asyncio.run(orbit.execute_hourly_scroll(None, when, False,
                                                    slot_override='after-42'))
            like.assert_not_called()

    def test_rolling_cycle_likes_reacts_and_shares_once(self):
        url = 'https://x.com/SinClair_0000/status/999'
        when = datetime(2026, 11, 4, 14, 0, tzinfo=orbit.IST)
        own = SimpleNamespace(id=42, out=True, message=url,
                              date=datetime(2026, 11, 4, 13, 30, tzinfo=orbit.IST))
        links = [SimpleNamespace(id=i, out=False,
                 message=f'https://x.com/user{i}/status/{100+i}') for i in range(43, 53)]
        client = AsyncMock()
        client.send_message.return_value = SimpleNamespace(id=53)
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(orbit, 'OUT', Path(temp)), \
             patch.object(orbit, 'STATE', Path(temp) / 'state.json'), \
             patch.object(orbit, 'post_scroll_window', return_value=(
                 datetime(2026, 11, 4, 13, 0, tzinfo=orbit.IST),
                 datetime(2026, 11, 4, 18, 0, tzinfo=orbit.IST), url)), \
             patch.object(orbit, 'now_ist', return_value=when), \
             patch.object(orbit, 'group_and_topic', new_callable=AsyncMock,
                          return_value=('chat', SimpleNamespace(id=1, closed=False))), \
             patch.object(orbit, 'messages_in_topic', new_callable=AsyncMock,
                          return_value=[own] + links), \
             patch.object(orbit, 'ensure_like',
                          side_effect=lambda state, key, tid: state.update({key: 'done'})) as like, \
             patch.object(orbit, 'telegram_react', new_callable=AsyncMock) as react:
            asyncio.run(orbit.execute_hourly_scroll(client, when, False,
                                                    slot_override='after-42',
                                                    window_end=datetime(2026, 11, 4, 18, 0,
                                                                        tzinfo=orbit.IST)))
            asyncio.run(orbit.execute_hourly_scroll(client, when, False,
                                                    slot_override='after-42',
                                                    window_end=datetime(2026, 11, 4, 18, 0,
                                                                        tzinfo=orbit.IST)))
            self.assertEqual(like.call_count, 10)
            self.assertEqual(react.await_count, 10)
            client.send_message.assert_awaited_once_with('chat', url, reply_to=1,
                                                          link_preview=False)
            state = json.loads((Path(temp) / 'state.json').read_text())
            self.assertEqual(state['2026-11-04:after-42:complete'], 'done')
            self.assertEqual(state['2026-11-04:scroll:last_anchor'], 53)

    def test_uncertain_scroll_share_blocks_reposting(self):
        with self.assertRaises(RuntimeError):
            orbit.assert_no_uncertain_scroll_share({
                '2026-11-04:post-start:posted': 'pending'}, '2026-11-04')
        with self.assertRaises(RuntimeError):
            orbit.assert_no_uncertain_scroll_share({
                '2026-11-04:after-42:posted': 'pending'}, '2026-11-04')

    def test_mega_submission_waits_for_live_session_links(self):
        url = 'https://x.com/SinClair_0000/status/999'
        when = datetime(2026, 11, 4, 20, 5, tzinfo=orbit.IST)
        client = AsyncMock()
        with patch.object(orbit, 'post_scroll_window', return_value=(
                 datetime(2026, 11, 4, 13, 0, tzinfo=orbit.IST),
                 datetime(2026, 11, 4, 18, 0, tzinfo=orbit.IST), url)), \
             patch.object(orbit, 'posted_tweet_before', return_value=('2026-11-04', url)), \
             patch.object(orbit, 'group_and_topic', new_callable=AsyncMock,
                          return_value=('chat', SimpleNamespace(id=1, closed=False))), \
             patch.object(orbit, 'messages_in_topic', new_callable=AsyncMock,
                          return_value=[]):
            asyncio.run(orbit.execute(client, 'mega-post', when, False))
        client.send_message.assert_not_awaited()

    def test_regular_scroll_recheck_replaces_oldest_link_when_new_one_arrives(self):
        def msg(mid, author):
            return SimpleNamespace(id=mid, message=f'https://x.com/{author}/status/{mid}')
        first = [msg(i, f'user{i}') for i in range(1, 11)]
        self.assertEqual([x['message_id'] for x in orbit.latest_scroll_links(first, 'SinClair_0000')],
                         list(range(10, 0, -1)))
        with_new = first + [msg(11, 'SinClair_0000'), msg(12, 'new_member')]
        self.assertEqual([x['message_id'] for x in orbit.latest_scroll_links(with_new, 'SinClair_0000')],
                         [12] + list(range(10, 1, -1)))

    def test_no_scroll_action_after_five_hour_cutoff(self):
        end = datetime(2026, 11, 1, 18, 0, tzinfo=orbit.IST)
        with patch.object(orbit, 'now_ist', return_value=end):
            with self.assertRaises(orbit.ScrollWindowEnded):
                orbit.require_scroll_time(end)

    def test_official_mega_file_engages_only_visible_links_and_marks_partial(self):
        when = datetime(2026, 11, 4, 20, 40, tzinfo=orbit.IST)
        date = datetime(2026, 11, 4, 14, 40, tzinfo=timezone.utc)
        own_url = 'https://x.com/SinClair_0000/status/1'
        close_date = datetime(2026, 11, 4, 15, 0, tzinfo=timezone.utc)
        document = ('2026-11-04 15:00 UTC\n' + own_url +
                    '\nhttps://x.com/member/status/2\nhttps://x.com/missing/status/3\n')
        messages = [SimpleNamespace(id=5, date=close_date, message='',
                                    file=SimpleNamespace(name='links.txt')),
                    SimpleNamespace(id=4, date=close_date, message='Total Links: 3'),
                    SimpleNamespace(id=2, date=date, message='https://x.com/member/status/2'),
                    SimpleNamespace(id=1, date=date, message=own_url)]
        client = AsyncMock()
        client.download_media.return_value = document.encode()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'state.json').write_text(json.dumps({'2026-11-04:mega-20:posted': 'done'}))
            with patch.object(orbit, 'OUT', root), \
                 patch.object(orbit, 'STATE', root / 'state.json'), \
                 patch.object(orbit, 'group_and_topic', new_callable=AsyncMock,
                              return_value=('chat', SimpleNamespace(id=1))), \
                 patch.object(orbit, 'messages_in_topic', new_callable=AsyncMock,
                              return_value=messages), \
                 patch.object(orbit, 'posted_tweet_before', return_value=('2026-11-04', own_url)), \
                 patch.object(orbit, 'draft_replies', return_value=([{'id': '2'}],
                              [{'id': '2', 'reply': 'A relevant four word reply'}])) as drafts, \
                 patch.object(orbit, 'ensure_like') as like, \
                 patch.object(orbit, 'ensure_reply') as reply, \
                 patch.object(orbit, 'telegram_react', new_callable=AsyncMock) as react:
                asyncio.run(orbit.execute(client, 'mega-engage', when, False))
            client.download_media.assert_awaited_once()
            self.assertEqual([x['id'] for x in drafts.call_args.args[0]], ['2'])
            like.assert_called_once()
            reply.assert_called_once()
            react.assert_awaited_once()
            state = json.loads((root / 'state.json').read_text())
            self.assertEqual(state['2026-11-04:mega-20:partial'], 'done')
            self.assertNotIn('2026-11-04:mega-20:complete', state)

    def test_evening_mega_uses_same_day_post(self):
        history = {'2026-10-31': {'post_tweet_id': '123'},
                   '2026-11-01': {'post_tweet_id': '456'}}
        with patch.object(orbit.run_daily, 'read_state', return_value=history):
            day, url = orbit.posted_tweet_before(datetime(2026, 11, 1, 20, 5, tzinfo=orbit.IST))
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
