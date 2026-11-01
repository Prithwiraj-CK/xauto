import io
import json
import socket
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import x_actions


class WriteRetryTests(unittest.TestCase):
    def test_nested_x_error_is_not_recorded_as_success(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(x_actions, 'LOCK', Path(temp) / 'lock'), \
             patch.object(x_actions, 'guard'), patch.object(x_actions, 'cookies', return_value='cookie'), \
             patch.object(x_actions, 'need', return_value='proxy'), \
             patch.object(x_actions, 'record') as record, \
             patch.object(x_actions, 'post', return_value={'status': 'success', 'data': {
                 'response': json.dumps({'errors': [{'code': 433, 'message': 'Replies restricted'}]})}}):
            with self.assertRaises(SystemExit):
                x_actions.act('create_tweet_v2', {'tweet_text': 'reply'})
            record.assert_not_called()

    def test_already_liked_counts_as_success(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(x_actions, 'LOCK', Path(temp) / 'lock'), \
             patch.object(x_actions, 'guard'), patch.object(x_actions, 'cookies', return_value='cookie'), \
             patch.object(x_actions, 'need', return_value='proxy'), \
             patch.object(x_actions, 'record') as record, \
             patch.object(x_actions, 'post', return_value={'status': 'success', 'data': {
                 'response': json.dumps({'errors': [{'code': 139, 'message': 'already favorited'}]})}}):
            x_actions.act('like_tweet_v2', {'tweet_id': '123'})
            record.assert_called_once()

    def test_explicit_rate_limit_retries_then_succeeds(self):
        rejected = urllib.error.HTTPError('url', 429, 'rate limit', {'Retry-After': '2'}, io.BytesIO(b''))
        success = io.BytesIO(json.dumps({'status': 'success'}).encode())
        with patch.dict('os.environ', {'TWITTERAPI_KEY': 'test'}), \
             patch.object(x_actions.urllib.request, 'urlopen', side_effect=[rejected, success]) as request, \
             patch.object(x_actions.time, 'sleep') as sleep:
            self.assertEqual(x_actions.post('like_tweet_v2', {'tweet_id': '123'})['status'], 'success')
            self.assertEqual(request.call_count, 2)
            sleep.assert_called_once_with(2)

    def test_dns_failure_retries_but_timeout_does_not(self):
        dns = urllib.error.URLError(socket.gaierror(8, 'name not known'))
        success = io.BytesIO(json.dumps({'status': 'success'}).encode())
        with patch.dict('os.environ', {'TWITTERAPI_KEY': 'test'}), \
             patch.object(x_actions.urllib.request, 'urlopen', side_effect=[dns, success]) as request, \
             patch.object(x_actions.time, 'sleep'):
            self.assertEqual(x_actions.post('like_tweet_v2', {'tweet_id': '123'})['status'], 'success')
            self.assertEqual(request.call_count, 2)
        timeout = urllib.error.URLError(TimeoutError('timed out'))
        with patch.dict('os.environ', {'TWITTERAPI_KEY': 'test'}), \
             patch.object(x_actions.urllib.request, 'urlopen', side_effect=timeout) as request, \
             patch.object(x_actions.time, 'sleep') as sleep:
            with self.assertRaises(urllib.error.URLError):
                x_actions.post('like_tweet_v2', {'tweet_id': '123'})
            request.assert_called_once()
            sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
