import hashlib
import re
import typing as tp
from functools import partial

import imageio
import numpy as np
import yaml


def write_video(
    dst_file: str,
    frames: tp.List[np.ndarray],
    fps: int = 30,
    **kwargs,
):
    """! Writes the provided list of frames (video) to a local video file.
    @param dst_file (str) Full destination video file.
    @param frames (tp.List[np.ndarray]) List of video frames in RGB.
    @param fps (int, optional) Desired FPS of the video. Defaults to 30.
    """
    with imageio.get_writer(dst_file, fps=fps, **kwargs) as writer:
        for image in frames:
            writer.append_data(image)



def read_yaml(filename: str) -> tp.Dict[str, tp.Any]:
    """!

    @param filename (str) Reads a yaml file and returns the content as a dict.

    @return tp.Dict[str, tp.Any] Dictionary with contents of yaml.
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


def get_bucket_and_path(gcs_full_path: str) -> tp.Tuple[str]:
    """Splits a google cloud storage path into bucket_name and the rest
    of the path without the 'gs://' at the beginning
    Args:
        gcs_full_path (str): A valid Gcloud Storage path
    Raises:
        ValueError: If input path does not start with gs://
    Returns:
        tp.Tuple[str]: Bucket name and the rest of the path
    """
    m = re.match(r"(gs://)([^/]+)/(.*)", gcs_full_path)

    if m is None:
        raise ValueError("path is not valid, it needs to start with 'gs://'")

    bucket = m.group(2)
    file_path = m.group(3)
    return bucket, file_path
