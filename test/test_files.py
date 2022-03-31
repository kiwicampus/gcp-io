import unittest
import urllib.request
import os
import json
from typing import Any, Dict

from gcp_io.gcp_interface import GCPInterface

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
    
    def test_dowload_files(self):
        gcs_url = "gs://gcp-io-tests/files/test_donwload.json"
        downloaded_file = interface.download_file(gcs_url, "test_donwload.json")
        os.remove("test_donwload.json") 
        assert downloaded_file is True

    def test_repeated_dowload_files(self):
        gcs_url = "gs://gcp-io-tests/files/test_donwload.json"
        interface.download_file(gcs_url, "test_donwload.json")
        downloaded_file = interface.download_file(gcs_url, "test_donwload.json")
        os.remove("test_donwload.json") 
        assert downloaded_file is False

    def test_upload_files(self):
        gcs_url = "gs://gcp-io-tests/files/test_donwload.json"
        interface.download_file(gcs_url, "test_donwload.json")
        with open("test_donwload.json", "r") as json_downloaded :
            data = json.load(json_downloaded)
            data["C"] = 3
            with open("test_donwload_updated.json", "w") as json_updated:
                json.dump(data,json_updated)
        uploaded_file = interface.upload_file("test_donwload_updated.json", gcs_url)
        interface.upload_file("test_donwload.json", gcs_url)
        os.remove("test_donwload.json")
        os.remove("test_donwload_updated.json") 
        assert uploaded_file is True

    def test_upload_repeated_files(self):
        gcs_url = "gs://gcp-io-tests/files/test_donwload.json"
        interface.download_file(gcs_url, "test_donwload.json")
        uploaded_file = interface.upload_file("test_donwload.json", gcs_url)
        os.remove("test_donwload.json") 
        assert uploaded_file is False