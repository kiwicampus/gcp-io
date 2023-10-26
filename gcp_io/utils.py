import hashlib
import re
from functools import partial
from typing import Any, Dict, Generator, List, Tuple

import imageio
import numpy as np
import yaml


def write_video(
    dst_file: str,
    frames: List[np.ndarray],
    fps: int = 30,
    **kwargs,
):
    """! Writes the provided list of frames (video) to a local video file.
    @param dst_file (str) Full destination video file.
    @param frames (List[np.ndarray]) List of video frames in RGB.
    @param fps (int, optional) Desired FPS of the video. Defaults to 30.
    """
    with imageio.get_writer(dst_file, fps=fps, **kwargs) as writer:
        for image in frames:
            writer.append_data(image)


def read_yaml(filename: str) -> Dict[str, Any]:
    """!

    @param filename (str) Reads a yaml file and returns the content as a dict.

    @return Dict[str, Any] Dictionary with contents of yaml.
    """
    with open(filename, "r") as stream:
        data_loaded = yaml.safe_load(stream)
        return data_loaded


def md5sum(file_path: str) -> str:
    """Returns the md5 sum hash of a given LOCAL file

    @param file_path (str) Full path to file

    @return str Md5 hash string
    """
    with open(file_path, mode="rb") as f:
        d = hashlib.md5()
        for buf in iter(partial(f.read, 1024), b""):
            d.update(buf)
    return d.hexdigest()


def signed2gcs(signed_url: str) -> str:
    """!
    Converts a signed URL to a GCS path. The signed urls
    have the form: https://storage.googleapis.com/gcs_path?X-Goog-Algorithm=...
    @param signed_url string with signed URL
    @return string with GCS path
    """
    gcs_url = signed_url.replace("https://storage.googleapis.com/", "gs://")
    gcs_url = gcs_url.split("?")[0]
    return gcs_url


def get_bucket_and_path(gcs_full_path: str) -> Tuple[str]:
    """Splits a google cloud storage path into bucket_name and the rest
    of the path without the 'gs://' at the beginning
    Args:
        gcs_full_path (str): A valid Gcloud Storage path
    Raises:
        ValueError: If input path does not start with gs://
    Returns:
        Tuple[str]: Bucket name and the rest of the path
    """
    m = re.match(r"(gs://)([^/]+)/(.*)", gcs_full_path)

    if m is None:
        raise ValueError("path is not valid, it needs to start with 'gs://'")

    bucket = m.group(2)
    file_path = m.group(3)
    return bucket, file_path


def decode_video(video_bytes: bytes) -> Tuple[List[np.ndarray], Dict[str, Any]]:
    """! Decodes video from bytes to numpy array and metadata dict.
        It uses ffmpeg as backend.
    @param video_bytes (bytes) Video bytes.
    @return Tuple[List[np.ndarray], Dict[str, Any]] List of frames and metadata.
    """
    frames = []
    with imageio.get_reader(video_bytes, "ffmpeg") as reader:
        meta = reader.get_meta_data()
        for image in reader:
            frames.append(image)
    return frames, meta


def decode_video_gen(
    video_bytes: bytes,
) -> Generator[Tuple[np.ndarray, Dict[str, Any]], None, None]:
    """! Decodes video from bytes to numpy array and metadata dict.
        It uses ffmpeg as backend.
    @param video_bytes (bytes) Video bytes.
    @return Tuple[List[np.ndarray], Dict[str, Any]] List of frames and metadata.
    """
    with imageio.get_reader(video_bytes, "ffmpeg") as reader:
        meta = reader.get_meta_data()
        for image in reader:
            yield image, meta
