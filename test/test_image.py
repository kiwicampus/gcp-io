import unittest

import numpy as np
from gcp_io import GCPInterface

interface = GCPInterface()


class TestImageMethods(unittest.TestCase):
    def read_write_test(seld, dst_file: str, orig_image: np.ndarray):
        interface.write_image(dst_file, orig_image)
        image = interface.read_image(dst_file)
        assert orig_image.shape == image.shape
        np.testing.assert_array_equal(image, orig_image)

    def test_read_image_rgb(self):
        orig_image = np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8)
        self.read_write_test("gs://gcp-io-tests/image/image_rgb.png", orig_image)

    def test_read_image_gray(self):
        orig_image = np.random.randint(0, 255, (32, 32), dtype=np.uint8)
        self.read_write_test("gs://gcp-io-tests/image/image_gray.png", orig_image)

    def test_read_image_rgba(self):
        orig_image = np.random.randint(0, 255, (32, 32, 4), dtype=np.uint8)
        self.read_write_test("gs://gcp-io-tests/image/image_rgba.png", orig_image)
