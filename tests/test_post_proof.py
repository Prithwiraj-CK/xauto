import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import post_contract as contract
import post_publish as publisher
import run_daily
import scheduled_run
import send_post
import x_actions

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a1ZkAAAAASUVORK5CYII=')
SOURCE = 'https://x.com/subject/status/123'
RECEIPT = 'https://explorer.example/tx/receipt'


class ProofTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'receipt.png').write_bytes(PNG)
        self.post = {
            'type': 'hot-take', 'content_kind': 'investigation',
            'text': 'so @subject, why did these wallets buy early?',
            'source_tweet_url': SOURCE, 'quote_tweet_url': SOURCE,
            'subject_handles': ['subject'], 'images': ['receipt.png'],
            'sources': [{'url': url, 'claim': 'fixture fact', 'checked_at': '2026-01-01T00:00:00Z'}
                        for url in (SOURCE, RECEIPT)],
            'source_reply': 'original analysis, oct 14. attribution remains unconfirmed. ' + RECEIPT,
            'image_proof': [{'path': 'receipt.png', 'kind': 'screenshot', 'source_url': RECEIPT,
                             'claim': 'fixture fact', 'credit': 'test source',
                             'captured_at': '2026-01-01T00:00:00Z',
                             'sha256': hashlib.sha256(PNG).hexdigest(),
                             'visual_review': {'readable': True, 'authentic': True, 'supports_claim': True}}],
        }

    def tweet(self, tid='10', is_reply=False):
        text = self.post['source_reply'] if is_reply else self.post['text']
        return {'id': tid, 'author': {'userName': 'SinClair_0000'}, 'text': text,
                'inReplyToId': '10' if is_reply else None,
                'quoted_tweet': None if is_reply else {'id': '123'},
                'extendedEntities': {'media': [] if is_reply else [{'type': 'photo', 'url': 'https://t.co/media'}]},
                'entities': {'user_mentions': [] if is_reply else [{'screen_name': 'subject'}]}}

    def mocks(self):
        # All external writes/reads are mocked. Never exercise live account actions.
        from contextlib import ExitStack
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(x_actions, 'load_env'))
        stack.enter_context(patch.dict('os.environ', {'X_BOT_USERNAME': 'SinClair_0000'}))
        stack.enter_context(patch.object(publisher.time, 'sleep'))
        upload = stack.enter_context(patch.object(x_actions, 'upload_image', return_value='media-1'))
        act = stack.enter_context(patch.object(x_actions, 'act', side_effect=[{'tweet_id': '10'}, {'tweet_id': '11'}]))
        get = stack.enter_context(patch.object(publisher, 'get_tweet', side_effect=lambda tid: self.tweet(tid, tid == '11')))
        return act, get, upload

    def test_manual_quote_allowed_but_daily_quote_rejected(self):
        contract.validate_post(self.post, self.root)
        with patch.object(scheduled_run, 'ROOT', self.root):
            with self.assertRaisesRegex(ValueError, 'quote tweets are disabled'):
                scheduled_run.validate_post(self.post, '2026-11-03')

    def test_original_daily_post_with_authentic_proof_allowed(self):
        post = {**self.post, 'type': 'meteora', 'content_kind': 'research',
                'text': 'the linked pool data shows the position value',
                'subject_handles': [], 'sources': self.post['sources'][1:]}
        post.pop('source_tweet_url')
        post.pop('quote_tweet_url')
        with patch.object(scheduled_run, 'ROOT', self.root):
            scheduled_run.validate_post(post, '2026-11-04')

    def test_missing_tag_wrong_quote_or_missing_images_rejected(self):
        changes = [{'text': 'subject, why did these wallets buy early?'},
                   {'quote_tweet_url': 'https://x.com/subject/status/999'},
                   {'images': [], 'image_proof': []}, {'content_kind': None}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                contract.validate_post({**self.post, **change}, self.root)

    def test_opinion_label_cannot_drop_external_quote_tag(self):
        bad = {**self.post, 'content_kind': 'opinion', 'subject_handles': [], 'text': 'a vague callout'}
        with self.assertRaisesRegex(ValueError, '@mention'):
            contract.validate_post(bad, self.root)

    def test_changed_or_unreviewed_image_and_note_only_sources_rejected(self):
        (self.root / 'receipt.png').write_bytes(PNG + b'changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            contract.validate_post(self.post, self.root)
        (self.root / 'receipt.png').write_bytes(PNG)
        bad = deepcopy(self.post); bad['image_proof'][0]['visual_review']['readable'] = False
        with self.assertRaises(ValueError):
            contract.validate_post(bad, self.root)
        bad = {**self.post, 'source_reply': '', 'note': 'put the links in a reply'}
        with self.assertRaisesRegex(ValueError, 'source_reply'):
            contract.validate_post(bad, self.root)

    def test_publisher_sends_quote_and_images_and_actual_source_reply(self):
        act, get, upload = self.mocks()
        self.assertEqual(publisher.publish_post(self.post, self.root), '10')
        body = act.call_args_list[0].args[1]
        self.assertEqual(body['attachment_url'], SOURCE)
        self.assertEqual(body['media_ids'], ['media-1'])
        self.assertEqual(act.call_args_list[1].args[1]['reply_to_tweet_id'], '10')
        self.assertNotIn('attachment_url', act.call_args_list[1].args[1])
        self.assertEqual(Path(upload.call_args.args[0]).read_bytes(), PNG)
        # A resumed completed package verifies, but never publishes again.
        publisher.publish_post(self.post, self.root)
        self.assertEqual(act.call_count, 2)
        self.assertEqual(upload.call_count, 1)

    def test_main_verification_failure_resumes_without_duplicate(self):
        act, get, _ = self.mocks()
        wrong = self.tweet(); wrong['quoted_tweet'] = None
        get.side_effect = None; get.return_value = wrong
        with self.assertRaisesRegex(RuntimeError, 'Do not repost'):
            publisher.publish_post(self.post, self.root)
        self.assertEqual(act.call_count, 1)
        get.side_effect = lambda tid: self.tweet(tid, tid == '11')
        publisher.publish_post(self.post, self.root)
        self.assertEqual(act.call_count, 2)
        self.assertIn('reply_to_tweet_id', act.call_args.args[1])

    def test_uncertain_submission_blocks_same_and_changed_drafts(self):
        act, _, _ = self.mocks()
        act.side_effect = TimeoutError('ambiguous write')
        with self.assertRaises(TimeoutError):
            publisher.publish_post(self.post, self.root)
        with self.assertRaisesRegex(RuntimeError, 'Uncertain'):
            publisher.publish_post(self.post, self.root)
        changed = {**self.post, 'text': 'so @subject, can you explain this timing?'}
        with self.assertRaisesRegex(RuntimeError, 'earlier publication'):
            publisher.publish_post(changed, self.root)
        self.assertEqual(act.call_count, 1)

    def test_source_verification_failure_keeps_both_ids(self):
        act, get, _ = self.mocks()
        wrong = self.tweet('11', True); wrong['inReplyToId'] = '999'
        get.side_effect = lambda tid: self.tweet() if tid == '10' else wrong
        with self.assertRaises(RuntimeError):
            publisher.publish_post(self.post, self.root)
        get.side_effect = lambda tid: self.tweet(tid, tid == '11')
        publisher.publish_post(self.post, self.root)
        self.assertEqual(act.call_count, 2)

    def test_live_verification_rejects_missing_tag_media_and_wrong_account(self):
        with patch.dict('os.environ', {'X_BOT_USERNAME': 'SinClair_0000'}):
            for field, value in [('entities', {}), ('extendedEntities', {}),
                                 ('author', {'userName': 'someoneelse'}), ('text', 'wrong text')]:
                with self.subTest(field=field), self.assertRaises(ValueError):
                    publisher.verify_tweet({**self.tweet(), field: value}, self.post['text'], SOURCE, 1)

    def test_daily_blocks_quotes_while_manual_publisher_keeps_the_package_path(self):
        (self.root / 'out').mkdir(); path = self.root / 'out/post.json'
        path.write_text(json.dumps(self.post)); (self.root / '.env').write_text('')
        with patch.object(run_daily, 'ROOT', self.root), patch.object(run_daily, 'POST', path), \
             patch.object(run_daily, 'log'), patch.object(run_daily, 'publish_post', return_value='10') as publish:
            self.assertIsNone(run_daily.post_daily(False))
            publish.assert_not_called()
        with patch.object(send_post, 'ROOT', self.root), patch.object(send_post, 'send'), \
             patch.object(send_post, 'publish_post', return_value='10') as publish, \
             patch.dict('os.environ', {}, clear=True):
            send_post.main(); publish.assert_called_once_with(self.post, self.root)

    def test_live_text_expands_source_links_and_allows_only_attachment_suffix(self):
        with patch.dict('os.environ', {'X_BOT_USERNAME': 'SinClair_0000'}):
            tweet = self.tweet()
            tweet['text'] += ' https://t.co/media https://t.co/quote'
            tweet['entities']['urls'] = [{'url': 'https://t.co/quote', 'expanded_url': SOURCE}]
            publisher.verify_tweet(tweet, self.post['text'], SOURCE, 1)
            reply = self.tweet('11', True)
            reply['text'] = reply['text'].replace(RECEIPT, 'https://t.co/source')
            reply['entities']['urls'] = [{'url': 'https://t.co/source', 'expanded_url': RECEIPT}]
            publisher.verify_tweet(reply, self.post['source_reply'], parent='10')
            tweet['text'] += ' unexpected'
            with self.assertRaises(ValueError):
                publisher.verify_tweet(tweet, self.post['text'], SOURCE, 1)

    def test_quote_cli_passes_images_without_losing_quote(self):
        with patch.object(x_actions, 'upload_image', return_value='media') as upload, patch.object(x_actions, 'act') as act:
            x_actions.cmd_qt(SOURCE, self.post['text'], ['receipt.png'])
            self.assertEqual(act.call_args.args[1]['attachment_url'], SOURCE)
            self.assertEqual(act.call_args.args[1]['media_ids'], ['media'])

    def test_reply_allows_x_inherited_mentions_and_cited_tweet_preview(self):
        text = 'source: ' + SOURCE
        reply = self.tweet('11', True)
        reply.update(text='@subject source: https://t.co/source', displayTextRange=[9, 35],
                     quoted_tweet={'id': '123'})
        reply['entities'] = {'user_mentions': [{'screen_name': 'subject'}],
                             'urls': [{'url': 'https://t.co/source', 'expanded_url': SOURCE}]}
        with patch.dict('os.environ', {'X_BOT_USERNAME': 'SinClair_0000'}):
            publisher.verify_tweet(reply, text, parent='10')
            reply['quoted_tweet'] = {'id': '999'}
            with self.assertRaises(ValueError):
                publisher.verify_tweet(reply, text, parent='10')


if __name__ == '__main__':
    unittest.main()
