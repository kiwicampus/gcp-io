import os
import unittest
from typing import List, Tuple, Union

import numpy as np
from gcp_io import GCPInterface

interface = GCPInterface()


class TestVideoMethods(unittest.TestCase):
    def setUp(self):
        self.local_video = "test.mp4"

    def tearDown(self):
        if os.path.exists(self.local_video):
            os.remove(self.local_video)

    def read_write_test(seld, dst_file: str, orig_video: List[np.ndarray]):
        interface.write_video(dst_file, orig_video, fps=15)
        video, meta = interface.read_video(dst_file)
        assert np.array(orig_video).shape == np.array(video).shape
        assert isinstance(meta, dict)
        assert meta["fps"] == 15

    def get_frames(
        self, shape: Union[Tuple[int, int, int], Tuple[int, int]], length: int
    ) -> List[np.ndarray]:
        frames = [
            np.random.randint(0, 255, shape, dtype=np.uint8) for _ in range(length)
        ]
        return frames

    def test_read_video_rgb(self):
        frames = self.get_frames((32, 32, 3), 10)
        self.read_write_test("gs://gcp-io-tests/video/video_rgb.mp4", frames)

    def test_read_video_rgb_local(self):
        frames = self.get_frames((32, 32, 3), 10)
        self.read_write_test(self.local_video, frames)

    # HINT: imageio seems to not support gray and rgba videos, always produces rgb videos
    # def test_read_video_gray(self):
    #     frames = self.get_frames((32, 32), 10)
    #     self.read_write_test("gs://gcp-io-tests/video/video_gray.mp4", frames)
    #     # self.read_write_test("video_gray.mp4", frames)

    # def test_read_video_rgba(self):
    #     frames = self.get_frames((32, 32, 4), 10)
    #     self.read_write_test("gs://gcp-io-tests/video/video_rgba.mp4", frames)
    #     # self.read_write_test("video_rgba.mp4", frames)
