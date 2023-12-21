"""This module contains tests for the Config class"""

import os
import unittest
from unittest import mock

from server.config import DailyAPIData, Config


class ConfigDomainEnvTest(unittest.TestCase):
    @mock.patch.dict(os.environ,
                     {
                         "DAILY_API_KEY": "abc123",
                     })
    def test_parse_default_env(self):
        c = Config()
        want_data = None
        got_data = c.get_daily_api_key("some-domain-name")
        self.assertEqual(got_data, want_data)

    @mock.patch.dict(os.environ,
                     {
                         "DAILY_API_KEY_MYDOMAIN": "abc123",
                     })
    def test_parse_custom_domain(self):
        c = Config()
        want_data = DailyAPIData("mydomain", None, "abc123")
        got_data = c.get_daily_api_key("mydomain")
        self.assertDictEqual(got_data.__dict__, want_data.__dict__)

    @mock.patch.dict(os.environ,
                     {
                         "DAILY_API_KEY_MYDOMAIN_STAGING": "abc123",
                         "DAILY_API_KEY_MYDOMAIN2": "def456",
                     })
    def test_parse_custom_domain_and_env(self):
        c = Config()
        want_data = DailyAPIData("mydomain", "staging", "abc123")
        got_data = c.get_daily_api_key("mydomain")
        self.assertDictEqual(got_data.__dict__, want_data.__dict__)

        got_api_endpoint = got_data.get_api_url()
        want_api_endpoint = "https://api.staging.daily.co/v1/"
        self.assertEqual(got_api_endpoint, want_api_endpoint)

        want_data = DailyAPIData("mydomain2", None, "def456")
        got_data = c.get_daily_api_key("mydomain2")
        self.assertDictEqual(got_data.__dict__, want_data.__dict__)

        got_api_endpoint = got_data.get_api_url()
        want_api_endpoint = "https://api.daily.co/v1/"
        self.assertEqual(got_api_endpoint, want_api_endpoint)
