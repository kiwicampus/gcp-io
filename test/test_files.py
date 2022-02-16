import unittest
import urllib.request
from typing import Any, Dict

from gcp_io import GCPInterface

interface = GCPInterface()


class TestFilesMethods(unittest.TestCase):
    def test_signed_url(self):
        gcs_url = "gs://gcp-io-tests/yaml/test_simple.yaml"
        signed_url = interface.gcs2signed(gcs_url, expiration_mins=1)
        url_request = urllib.request.Request(url=signed_url, method="GET")
        content = urllib.request.urlopen(url_request, timeout=5)
        assert content.read()

    def test_signed_url_error(self):
        gcs_url = "gs://gcp-io-tests/yaml/bad_file.yaml"
        with self.assertRaises(Exception):
            signed_url = interface.gcs2signed(gcs_url, expiration_mins=1)
            assert signed_url is None
