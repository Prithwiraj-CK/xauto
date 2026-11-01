import io
import json
import os
import sys
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import spend


class SpendStatusTests(unittest.TestCase):
    def test_proxy_period_and_renewal_label(self):
        data = {'end_date': '2026-11-11T12:00:00+00:00', 'renewals_enabled': True}
        now = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
        with patch.dict(os.environ, {'WEBSHARE_API_KEY': 'test'}), \
             patch.object(spend, 'get_json', return_value=data) as request:
            self.assertEqual(spend.proxy_status(now),
                             'Webshare proxy: 10.0 days until next renewal (period ends 2026-11-11)')
            self.assertEqual(request.call_args.args[1]['Authorization'], 'Token test')

    def test_missing_key_or_failed_check_is_not_a_fake_expiry(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIn('unavailable', spend.proxy_status())
        with patch.dict(os.environ, {'WEBSHARE_API_KEY': 'test'}), \
             patch.object(spend, 'get_json', side_effect=urllib.error.URLError('offline')):
            self.assertIn('subscription check failed', spend.proxy_status())

    def test_transient_status_request_retries(self):
        good = io.BytesIO(json.dumps({'end_date': '2026-11-11T12:00:00Z'}).encode())
        with patch.object(spend.urllib.request, 'urlopen', side_effect=[urllib.error.URLError('offline'), good]) as request, \
             patch.object(spend.time, 'sleep') as sleep:
            self.assertEqual(spend.get_json('https://example.test', {}),
                             {'end_date': '2026-11-11T12:00:00Z'})
            self.assertEqual(request.call_count, 2)
            sleep.assert_called_once_with(2)


if __name__ == '__main__':
    unittest.main()
