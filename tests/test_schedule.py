import hashlib
import json
from datetime import datetime
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] if Path(__file__).parent.name == 'tests' else Path(__file__).parent))
import scheduled_run as schedule
import reply_queue as queue
import run_daily as daily


class ScheduleTests(unittest.TestCase):
    def test_same_evening_and_wake_boundaries(self):
        for hour, minute, expected in [(9, 0, None), (21, 30, None), (21, 31, 'daily'), (23, 31, 'daily')]:
            now = datetime(2026, 11, 1, hour, minute, tzinfo=schedule.IST)
            self.assertEqual(schedule.session('daily', now), expected)
        for hour, expected in [(12, None), (13, 'replies-13'), (16, 'replies-15'), (20, 'replies-20'), (23, 'replies-23')]:
            self.assertEqual(schedule.session('replies', datetime(2026, 11, 1, hour, tzinfo=schedule.IST)), expected)

    def test_weekdays_and_proof(self):
        for day, topic in zip(range(2, 9), schedule.SLOTS):
            post = {'type': topic, 'text': 'what would you check first?'}
            if topic in daily.POST_TYPES_REQUIRING_PROOF:
                with self.assertRaises(ValueError):
                    schedule.validate_post(post, f'2026-11-{day:02d}')
                post['quote_tweet_url'] = 'https://x.com/source/status/123'
            schedule.validate_post(post, f'2026-11-{day:02d}')
        with self.assertRaises(ValueError):
            schedule.validate_post({'type': 'hot-take', 'text': 'my thought'}, '2026-11-01')
        with self.assertRaises(ValueError):
            schedule.validate_post({'type': 'journey', 'text': 'i earned [amount]'}, '2026-11-01')

    def test_reply_cap_sources_and_words(self):
        sources = [{'id': str(i), 'author': 'tester', 'text': f'source {i}'} for i in range(10)]
        drafts = [{**s, 'reply': 'what bin step?'} for s in sources]
        schedule.validate_replies(drafts, 10, sources)
        schedule.validate_replies([], 3, sources)
        with self.assertRaises(ValueError):
            schedule.validate_replies(drafts, 3, sources)
        bad = [{**drafts[0], 'id': '999'}]
        with self.assertRaises(ValueError):
            schedule.validate_replies(bad, 3, sources)
        with self.assertRaises(ValueError):
            schedule.validate_replies([{**d, 'reply': 'lol'} for d in drafts[:2]], 3, sources)

    def test_exact_hash_and_local_date(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'out').mkdir()
            post = root / 'out/post.json'; post.write_text('{}')
            state = {'drafted_for': '2026-11-01', 'generator': 'codex', 'post_sha256': hashlib.sha256(post.read_bytes()).hexdigest()}
            (root / 'out/draft_state.json').write_text(json.dumps(state))
            with patch.object(daily, 'ROOT', root), patch.object(daily, 'POST', post):
                self.assertTrue(daily.codex_draft_valid('2026-11-01', include_replies=False))
                self.assertFalse(daily.codex_draft_valid('2026-11-02', include_replies=False))
                post.write_text('{"changed":true}')
                self.assertFalse(daily.codex_draft_valid('2026-11-01', include_replies=False))

    def test_failed_post_does_not_stamp_success_or_queue_replies(self):
        with patch.object(daily, 'load_env'), patch.object(daily, 'log'), patch.object(daily, 'read_state', return_value={}), \
             patch.object(daily, 'codex_draft_valid', return_value=True), patch.object(daily, 'spend_start'), \
             patch.object(daily, 'spend_end'), patch.object(daily, 'webhook'), patch.object(daily, 'post_daily', return_value=None), \
             patch.object(daily, 'write_state') as write, patch.object(daily, 'queue_replies') as enqueue, \
             patch.object(sys, 'argv', ['run_daily.py', '--post-only']):
            self.assertEqual(daily.main(), 1)
            write.assert_not_called(); enqueue.assert_not_called()

    def test_posted_day_retry_does_not_regenerate_or_publish(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); (folder / 'backed_up.json').write_text('{}')
            with patch.object(daily, 'read_state', return_value={'2026-11-01': {'post_tweet_id':'123'}}), \
                 patch.object(schedule, 'generate') as generate, patch.object(schedule, 'checked') as checked:
                schedule.daily('2026-11-01', folder)
                generate.assert_not_called(); checked.assert_not_called()

    def test_same_day_draft_publishes_before_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); folder = root / 'out/scheduled/2026-11-01/daily'; folder.mkdir(parents=True)
            events = []
            now = datetime(2026, 11, 1, 21, 35, tzinfo=schedule.IST)
            with patch.object(schedule, 'ROOT', root), patch.object(daily, 'read_state', return_value={}), \
                 patch.object(daily, 'codex_draft_valid', return_value=False), patch.object(schedule, 'now_ist', return_value=now), \
                 patch.object(schedule, 'generate', return_value={'type':'journey', 'text':'what are you watching next week?'}), \
                 patch.object(schedule, 'checked', side_effect=lambda *a, **k: events.append('publish')), \
                 patch.object(schedule, 'push_draft', side_effect=lambda *a: events.append('backup')):
                schedule.daily('2026-11-01', folder)
            self.assertEqual(events, ['publish', 'backup'])
            self.assertEqual(json.loads((root / 'out/draft_state.json').read_text())['drafted_for'], '2026-11-01')

    def test_dry_run_does_not_call_spend_api(self):
        with patch.object(daily, 'load_env'), patch.object(daily, 'log'), patch.object(daily, 'read_state', return_value={}), \
             patch.object(daily, 'spend_start') as spend, patch.object(daily, 'post_daily', return_value='DRY'), \
             patch.object(sys, 'argv', ['run_daily.py', '--dry', '--post-only']):
            daily.main(); spend.assert_not_called()


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = patch.object(queue, 'DB', Path(self.tmp.name) / 'queue.sqlite3')
        self.patch.start()

    def tearDown(self):
        self.patch.stop(); self.tmp.cleanup()

    def draft(self, tid):
        return {'id': str(tid), 'author': 'tester', 'text': 'source', 'reply': 'what bin step?'}

    def test_append_during_processing_survives_and_deduplicates(self):
        self.assertEqual(queue.enqueue([self.draft(1)]), 1)
        first = queue.next_reply()
        self.assertEqual(queue.enqueue([self.draft(1), self.draft(2)]), 1)
        queue.finish(first['id'], 'sent')
        self.assertEqual(queue.next_reply()['id'], '2')
        self.assertEqual(queue.enqueue([self.draft(1)]), 0)
        queue.finish('2', 'sent')
        self.assertIsNone(queue.next_reply())

    def test_late_wake_respaces_pending_and_failed_item_retained(self):
        with patch.object(queue.time, 'time', return_value=1000), patch.object(queue.random, 'uniform', return_value=45):
            queue.enqueue([self.draft(1), self.draft(2), self.draft(3)])
        with patch.object(queue.time, 'time', return_value=20000), patch.object(queue.random, 'uniform', return_value=45):
            queue.finish('1', 'failed')
        self.assertEqual(queue.next_reply()['due'], 22700)
        with queue.connect() as conn:
            self.assertEqual(conn.execute("SELECT status FROM replies WHERE id='1'").fetchone()[0], 'failed')
            self.assertEqual(conn.execute("SELECT due FROM replies WHERE id='3'").fetchone()[0], 25400)


if __name__ == '__main__':
    unittest.main()
