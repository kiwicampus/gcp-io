import os
import unittest
from typing import Any, Dict

from gcp_io import GCPInterface

interface = GCPInterface()


class TestYamlMethods(unittest.TestCase):
    def setUp(self):
        self.local_yaml = "test.yaml"

    def tearDown(self):
        if os.path.exists(self.local_yaml):
            os.remove(self.local_yaml)

    def read_write_test(self, dst_file: str, orig_dict: Dict[Any, Any]):
        interface.write_yaml(dst_file, orig_dict)
        read_dict = interface.read_yaml(dst_file)
        self.assertCountEqual(orig_dict, read_dict)

    def test_read_simple_yaml(self):
        simple_dict = {
            "a": 1,
            "b": 2,
        }
        self.read_write_test("gs://gcp-io-tests/yaml/test_simple.yaml", simple_dict)

    def test_read_simple_yaml_local(self):
        simple_dict = {
            "a": 1,
            "b": 2,
        }
        self.read_write_test(self.local_yaml, simple_dict)
