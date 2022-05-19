import unittest
import urllib.request
import os
import json
from typing import Any, Dict

from gcp_io import GCPInterface

interface = GCPInterface()


class TestFilesMethods(unittest.TestCase):
    def test_signed_url(self):
        gcs_url = "gs://gcp-io-tests/yaml/test_simple.yaml"
        signed_url = interface.gcs2signed(gcs_url, expiration_mins=1)
        assert signed_url is not None
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
        interface.download_file(gcs_url, "test_donwload.json")
        downloaded_file = os.path.exists("test_donwload.json")
        os.remove("test_donwload.json")
        assert downloaded_file

    def test_repeated_dowload_files(self):
        gcs_url = "gs://gcp-io-tests/files/test_donwload.json"
        interface.download_file(gcs_url, "test_donwload.json")
        downloaded_file = interface.check_md5sum(gcs_url, "test_donwload.json")
        os.remove("test_donwload.json")
        assert downloaded_file

    def test_upload_files(self):
        gcs_url = "gs://gcp-io-tests/files/test_donwload.json"
        interface.download_file(gcs_url, "test_donwload.json")
        with open("test_donwload.json", "r") as json_downloaded:
            data = json.load(json_downloaded)
            data["C"] = 3
            with open("test_donwload_updated.json", "w") as json_updated:
                json.dump(data, json_updated)
        uploaded_file = interface.check_md5sum(gcs_url, "test_donwload_updated.json")
        interface.upload_file("test_donwload.json", gcs_url)
        os.remove("test_donwload.json")
        os.remove("test_donwload_updated.json")
        assert not uploaded_file

    def test_upload_file_no_exist(self):
        gcs_url = "gs://gcp-io-tests/files/test_donwload.json"
        interface.download_file(gcs_url, "test_donwload.json")
        new_gcs_file = "gs://gcp-io-tests/files/test_donwload_new.json"
        interface.upload_file("test_donwload.json", new_gcs_file)
        assert interface.file_exists(new_gcs_file)
        interface.remove_file(new_gcs_file)
        interface.remove_file("test_donwload.json")

    def test_upload_repeated_files(self):
        gcs_url = "gs://gcp-io-tests/files/test_donwload.json"
        interface.download_file(gcs_url, "test_donwload.json")
        uploaded_file = interface.check_md5sum(gcs_url, "test_donwload.json")
        os.remove("test_donwload.json")
        assert uploaded_file

