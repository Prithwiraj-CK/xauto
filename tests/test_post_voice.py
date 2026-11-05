"""Owner feedback regressions. No network calls or real publication."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import post_contract
import post_publish
import post_voice
import run_daily
import scheduled_run
import send_post


class VoiceTests(unittest.TestCase):
    def rejected(self):
        return json.loads(post_voice.FEEDBACK.read_text())

    def test_november_3_to_5_real_posts_and_spacing_variants_rejected(self):
        for item in self.rejected():
            with self.subTest(date=item['date']):
                self.assertTrue(post_voice.lint(item['text']))
                self.assertTrue(post_voice.lint(' '.join(item['text'].upper().split())))
                self.assertTrue(run_daily.lint_post(item['text']))

    def test_new_words_in_same_formula_still_rejected(self):
        text = ("routing got another update.\n\n@project added more routes. "
                "i would still check the price before using it.\n\nanyone using this yet?")
        self.assertTrue(any('formula:' in reason for reason in post_voice.lint(text)))

    def test_questions_material_uncertainty_and_concrete_disagreement_allowed(self):
        # Illustrative wording only; this test does not establish its factual claims.
        for text in [
            '@subject, why did the linked wallets buy before your call?',
            "@subject, that screenshot shows fees. where is the position value?",
            "wallet links aren't proof of ownership. the transfer shows funding, not who signed the trade.",
            "i'd check the date on that screenshot. it's from october, not today's launch.",
            "@subject, why were those wallets early?\n\n@researcher links them to the account.\n\ni want the explanation for that timing.",
        ]:
            with self.subTest(text=text):
                self.assertEqual(post_voice.lint(text), [])

    def test_scheduler_and_all_publish_paths_block_before_external_action(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'out').mkdir()
            text = self.rejected()[-1]['text']
            post = {'type': 'meteora', 'content_kind': 'reaction', 'text': text}
            path = root / 'out/post.json'; path.write_text(json.dumps(post))
            with self.assertRaisesRegex(ValueError, 'rejected editorial example'):
                scheduled_run.validate_post(post, '2026-11-05')
            with self.assertRaisesRegex(ValueError, 'Editorial rejection'):
                post_contract.validate_post(post, root)
            with patch.object(post_publish.x, 'act') as act, patch.object(post_publish.x, 'upload_image') as upload:
                with self.assertRaisesRegex(ValueError, 'Editorial rejection'):
                    post_publish.publish_post(post, root)
                act.assert_not_called(); upload.assert_not_called()
            with patch.object(run_daily, 'ROOT', root), patch.object(run_daily, 'POST', path), \
                 patch.object(run_daily, 'log'), patch.object(run_daily, 'publish_post') as publish:
                self.assertIsNone(run_daily.post_daily(False))
                publish.assert_not_called()
            with patch.object(send_post, 'ROOT', root), patch.object(send_post, 'send') as send, \
                 patch.object(send_post, 'publish_post') as publish:
                with self.assertRaisesRegex(ValueError, 'Editorial rejection'):
                    send_post.main()
                publish.assert_not_called(); send.assert_not_called()


if __name__ == '__main__':
    unittest.main()
