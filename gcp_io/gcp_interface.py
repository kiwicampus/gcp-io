import base64
import binascii
import datetime
import os
import tempfile
import typing as tp
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import yaml
from google.cloud import storage
from google.oauth2 import service_account

from .utils import write_video, md5sum, get_bucket_and_path


class GCPInterface(object):
    def __init__(self, client: tp.Optional[tp.Union[str, storage.Client]] = None):
        """Create a GCP interface with given a GCP client or a path to a GCP key file.
        This class implements the following functions for I/O to GCP storage:


        Args:
            client (tp.Optional[tp.Union[str, storage.Client]]): GCP storage
                client or path to a GCP service account file. If not provided it will
                try to create one from the defaults using the environment variable
                GOOGLE_APPLICATION_CREDENTIALS. Defaults to None.

        Raises:
            ValueError: Error if client is of unsupported type.
        """
        if client is None:
            self.client = storage.Client()
        elif isinstance(client, str):
            credentials = service_account.Credentials.from_service_account_file(client)
            self.client = storage.Client(credentials=credentials)
        elif isinstance(client, storage.Client):
            self.client = client
        else:
            raise ValueError("Invalid client type: {}".format(type(client)))

    def write_yaml(self, dst_file: str, data: tp.Dict[str, tp.Any]) -> None:
        """! Writes a yaml file.
        @param dst_file (str) dst_file to write
        @param data (tp.Dict[str, tp.Any]) Data to write
        """
        if "gs://" in dst_file:
            self.upload_data(
                dst_file,
                yaml.dump(data, default_flow_style=False),
                "application/x-yaml",
            )
        else:
            with open(dst_file, "w") as outfile:
                yaml.dump(data, outfile, default_flow_style=False)

    def gcs2signed(self, gcs_path: str, expiration_mins: int = 15) -> str:
        """Generates a v4 signed URL for downloading a blob.

        Note that this method requires a service account key file. You can not use
        this if you are using Application Default Credentials from Google Compute
        Engine or from the Google Cloud SDK.
        """
        url = None
        try:
            bucket, file_path = get_bucket_and_path(gcs_path)
            bucket = self.client.bucket(bucket)
            blob = bucket.blob(file_path)

            url = blob.generate_signed_url(
                version="v4",
                # This URL is valid for 15 minutes
                expiration=datetime.timedelta(minutes=expiration_mins),
                # Allow GET requests using this URL.
                method="GET",
            )
        except Exception as e:
            print(f"Error getting signed URL: {e}")

        return url

    def file_exists(self, file_path: str) -> bool:
        """! Checks if a file exists
        @param file_path (str) Full path to the file
        @returns (bool) True if file exists
        """
        if "gs://" in file_path:
            try:
                bucket_name, file_path = get_bucket_and_path(file_path)
                bucket = self.client.bucket(bucket_name)
                return bucket.blob(file_path).exists()
            except Exception as e:
                print(f"Error checking if file exists: {file_path}, {e}")
                # If some error, we assume it doesn't exists, we don't know
                return False
        else:
            return Path(file_path).exists()

    def get_blob(self, file_path: str) -> storage.Blob:
        """Gets GCP storage.Blob object of given GCS file.

        @param file_path (str) Full GCP file path, begins with gs://

        @return storage.Blob Object of file
        """
        bucket_name, file_path = get_bucket_and_path(file_path)
        # get bucket with name
        bucket = self.client.bucket(bucket_name)
        # get bucket data as blob
        return bucket.get_blob(file_path)

    def get_md5sum(self, file: str) -> str:
        """! Gets md5sum of file
        @param file (str) Full path to file
        @returns (str) md5sum
        """
        if "gs://" in file:
            md5_hash = binascii.hexlify(
                base64.urlsafe_b64decode(self.get_blob(file).md5_hash)
            ).decode("utf-8")
        else:
            md5_hash = md5sum(file)
        return md5_hash

    def upload_data(
        self,
        gcs_path: str,
        data: tp.Union[str, bytes],
        content_type: str = "image/png",
    ):
        """Uploads data to google cloud storage
        Args:
            gcs_path (str): Full path to the bucket file
            data (tp.Union[str,bytes]): Raw data to be uploaded
            content_type (str, optional): HTTP content type style for the raw data.
                Defaults to "image/png".
        Content Type for video options
            video/mpeg
            video/mp4
            video/quicktime
            video/x-ms-wmv
            video/x-msvideo
            video/x-flv
            video/webm
        Content type for image options
            image/gif
            image/jpeg
            image/png
            image/tiff
            image/vnd.microsoft.icon
            image/x-icon
            image/vnd.djvu
            image/svg+xml
        """
        bucket_name, file_path = get_bucket_and_path(gcs_path)
        bucket = self.client.bucket(bucket_name)
        bucket.blob(file_path).upload_from_string(data, content_type=content_type)

    def get_bytes(self, gcs_path: str) -> bytes:
        """Gets bytes data from google cloud storage
        Args:
            gcs_path (str): Full path to the bucket file
        Raises:
            ValueError: If input path does not start with gs://
        Returns:
            bytes: Raw data from the file
        """
        bucket_name, file_path = get_bucket_and_path(gcs_path)
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        return blob.download_as_bytes()

    def download_data(
        self,
        src_file: str,
        dst_file: str,
    ):
        """! Downloads the file from cloud storage to local file
        @param src_file (str) Full path to the file in cloud storage.
        @param dst_file (str) Full path to the file to be downloaded.
        """
        content_bytes = self.get_bytes(src_file)
        with open(dst_file, "wb") as f:
            f.write(content_bytes)

    def write_video(
        self,
        dst_file: tp.Union[str, BytesIO],
        frames: tp.List[np.ndarray],
        fps: int = 30,
        format: str = "mp4",
        **kwargs,
    ):
        """! Writes a video to a local file, remote file or BytesIO object.
        For remote file only GCP storage is supported.
        @param dst_file (tp.Union[str, BytesIO]) Path string or BytesIO object.
        @param frames (tp.List[np.ndarray]) Video list of frames in RGB.
        @param fps (int, optional) Desired FPS. Defaults to 30.
        @param format (str, optional) Format of the video in case dst_file is
            a BytesIO object. Defaults to "mp4".
        """
        if isinstance(dst_file, BytesIO):
            with tempfile.TemporaryDirectory() as tmp_dir:
                dst_path = os.path.join(tmp_dir, f"video.{format}")
                write_video(dst_path, frames, fps, **kwargs)
                with open(dst_path, "rb") as f:
                    dst_file.write(f.read())

            # return dst_file
        elif "gs://" in dst_file:
            video_bytes = BytesIO()
            format = Path(dst_file).suffix[1:]
            self.write_video(video_bytes, frames, fps, format, **kwargs)
            self.upload_data(dst_file, video_bytes.getvalue(), f"video/{format}")
            # self.upload_data(dst_file, video_bytes.getvalue(), "video/mpeg")
        else:
            write_video(dst_file, frames, fps, **kwargs)

    extension_to_content_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".tiff": "image/tiff",
        ".pgm": "application/octet-stream",
    }

    def write_image(
        self,
        dst_file: str,
        image: np.ndarray,
        encode_args: tp.List[int] = None,
    ):
        """! Writes the image to the destination file locally or cloud.
        For the moment only GCP storage is supported.
        @param dst_file (str) Full path to image.
        @param image (np.ndarray) Image as numpy array.
        @param encode_args (tp.List[int], optional) List with parameters
            for encoding with cv2.imencode. For example for JPG it could
            be [cv2.IMWRITE_JPEG_QUALITY, 80]. Defaults to None.
        """
        ext = Path(dst_file).suffix
        # change to BGR because cv2.imencode expects BGR
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        if encode_args:
            retval, encoded_bytes = cv2.imencode(ext, image, encode_args)
        else:
            retval, encoded_bytes = cv2.imencode(ext, image)

        if not retval:
            raise ValueError("image could not be encoded!")

        encoded_bytes = encoded_bytes.tobytes()

        if "gs://" in dst_file:
            content_type = self.extension_to_content_type[ext]
            self.upload_data(dst_file, encoded_bytes, content_type)
        else:
            with open(dst_file, "wb") as f:
                f.write(encoded_bytes)

    def list_dir(self, src_dir: str, delimiter=None) -> tp.List[str]:
        """Get the list of files/folders of a GCP directory recursively
        when no delimeter.

        Args:
            src_dir (str): GCP storeage directory
            delimiter ([str], optional): Delimeter. Defaults to None.

        Returns:
            tp.List[str]: List of results
        """
        bucket_name, file_path = get_bucket_and_path(src_dir)
        blobs = self.client.list_blobs(
            bucket_name, prefix=file_path, delimiter=delimiter
        )

        for blob in blobs:
            yield os.path.join("gs://", bucket_name, blob.name)


if __name__ == "__main__":
    pass
