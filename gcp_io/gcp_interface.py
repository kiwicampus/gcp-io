import base64
import binascii
import datetime
import logging
import os
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Generator, Iterator, List, Optional, Tuple, Union

import imageio as iio
import numpy as np
import yaml
from google.cloud import storage
from google.oauth2 import service_account

from .utils import (
    decode_video,
    decode_video_gen,
    get_bucket_and_path,
    md5sum,
    read_yaml,
    write_video,
)


class GCPInterface(object):
    def __init__(self, client: Optional[Union[str, storage.Client]] = None):
        """Create a GCP interface with given a GCP client or a path to a GCP key file.
        This class implements the following functions for I/O to GCP storage:


        Args:
            client (Optional[Union[str, storage.Client]]): GCP storage
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

    def read_yaml(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Reads a yaml file.

        Args:
            file_path (str): Full path to the file.
            **kwargs: Additional keyword arguments to be forwarded to the
                'get_bytes' method if the file is on Google Cloud Storage.

        Returns:
            Dict[str, Any]: Dictionary of file contents.

        Example of using **kwargs:
            read_yaml(file_path, start=10, end=50)
        """
        if "gs://" in file_path:
            return yaml.safe_load(self.get_bytes(file_path, **kwargs))
        else:
            return read_yaml(file_path)

    def write_yaml(self, dst_file: str, data: Dict[str, Any], **kwargs) -> None:
        """
        Writes a yaml file.

        Args:
            dst_file (str): Destination file to write.
            data (Dict[str, Any]): Data to write.
            **kwargs: Additional keyword arguments to be forwarded to the
                'upload_data' method if the file is on Google Cloud Storage.

        Example of using **kwargs:
            write_yaml(dst_file, data, custom_arg="value")
        """
        if "gs://" in dst_file:
            self.upload_data(
                dst_file,
                yaml.dump(data, default_flow_style=False),
                "application/x-yaml",
                **kwargs,
            )
        else:
            with open(dst_file, "w") as outfile:
                yaml.dump(data, outfile, default_flow_style=False)

    def gcs2signed(self, gcs_path: str, expiration_mins: int = 15, **kwargs) -> str:
        """Generates a v4 signed URL for downloading a blob.

        Note that this method requires a service account key file. You can not use
        this if you are using Application Default Credentials from Google Compute
        Engine or from the Google Cloud SDK.

        There is a workaround for this, which is using impersonated credentials.
        See: https://blog.salrashid.dev/articles/2021/cloud_sdk_missing_manual/gcs_signedurl/
        and https://cloud.google.com/iam/docs/impersonating-service-accounts.
        For that use the kwargs to pass custom credentials to the generate_signed_url function.
        """
        url = None
        try:
            bucket, file_path = get_bucket_and_path(gcs_path)
            bucket = self.client.bucket(bucket)
            blob = bucket.blob(file_path)

            url = blob.generate_signed_url(
                version="v4",
                # This URL is valid for expiration_mins minutes
                expiration=datetime.timedelta(minutes=expiration_mins),
                # Allow GET requests using this URL.
                method="GET",
                **kwargs,
            )
        except Exception as e:
            logging.exception(f"Error getting signed URL: {e}")

        return url

    def file_exists(self, file_path: str) -> bool:
        """! Checks if a file exists
        @param file_path (str) Full path to the file
        @returns (bool) True if file exists
        """
        if "gs://" in file_path:
            try:
                return self.blob(file_path).exists()
            except Exception as e:
                logging.exception(f"Error checking if file exists: {file_path}, {e}")
                # If some error, we assume it doesn't exists, we don't know
                return False
        else:
            return Path(file_path).exists()

    def remove_file(self, file_path: str) -> None:
        """Removes a file from GCS or local file system.

        Args:
            file_path (str): Full path to file
        """
        if "gs://" in file_path:
            blob = self.blob(file_path)
            blob.delete()
        else:
            os.remove(file_path)

    def get_blob(self, file_path: str) -> storage.Blob:
        """Gets GCP storage.Blob object of given GCS file.
        This will make an HTTP request. This is useful if you
        need the blob's metadata only.

        @param file_path (str) Full GCP file path, begins with gs://

        @return storage.Blob Object of file
        """
        bucket_name, file_path = get_bucket_and_path(file_path)
        # get bucket with name
        bucket = self.client.bucket(bucket_name)
        # get bucket data as blob
        return bucket.get_blob(file_path)

    def blob(self, file_path: str) -> storage.Blob:
        """Gets GCP storage.Blob object of given GCS file.
        This WON'T make an HTTP request.
        This is useful if you want to download or call other methods on the blob.

        @param file_path (str) Full GCP file path, begins with gs://

        @return storage.Blob Object of file
        """
        bucket_name, file_path = get_bucket_and_path(file_path)
        # get bucket with name
        bucket = self.client.bucket(bucket_name)
        # get bucket data as blob without an HTTP request
        return bucket.blob(file_path)

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

    def check_md5sum(self, gcs_file: str, local_file: str) -> bool:
        """! Check if there are differences between a local file and one in GCP
        @param gcs_file (str) Full path to the file in cloud storage.
        @param local_file (str) Full path to the local file.
        """
        # If file exists, check if it has different hash
        if os.path.exists(local_file) and self.file_exists(gcs_file):
            remote_filehash = self.get_md5sum(gcs_file)
            local_filehash = self.get_md5sum(local_file)
            if local_filehash == remote_filehash:
                return True
        return False

    def upload_data(
        self,
        gcs_path: str,
        data: Union[str, bytes],
        content_type: str = "image/png",
        num_retries: int = 3,
        **kwargs,
    ):
        """
        Uploads data to google cloud storage.

        Args:
            gcs_path (str): Full path to the bucket file.
            data (Union[str,bytes]): Raw data to be uploaded.
            content_type (str, optional): HTTP content type style for the raw data.
                Defaults to "image/png".
            num_retries (int, optional): Number of retries in case of failure.
            **kwargs: Additional keyword arguments to be forwarded to the
                'upload_from_string' method of the blob object.

        Content Type for video options:
            video/mpeg
            video/mp4
            video/quicktime
            video/x-ms-wmv
            video/x-msvideo
            video/x-flv
            video/webm

        Content type for image options:
            image/gif
            image/jpeg
            image/png
            image/tiff
            image/vnd.microsoft.icon
            image/x-icon
            image/vnd.djvu
            image/svg+xml

        Example of using **kwargs:
            upload_data(gcs_path, data, content_type="video/mp4", custom_arg="value")
        """
        self.blob(gcs_path).upload_from_string(
            data, content_type=content_type, num_retries=num_retries, **kwargs
        )

    def get_bytes(self, gcs_path: str, **kwargs) -> bytes:
        """
        Gets bytes data from google cloud storage.

        Args:
            gcs_path (str): Full path to the bucket file.
            **kwargs: Additional keyword arguments to be forwarded to the
                'download_as_bytes' method of the blob object.

        Raises:
            ValueError: If input path does not start with gs://.

        Returns:
            bytes: Raw data from the file.

        Example of using **kwargs:
            get_bytes(gcs_path, start=10, end=50)
        """
        blob = self.blob(gcs_path)
        return blob.download_as_bytes(**kwargs)

    def download_file(
        self, src_file: str, dst_file: str, md5sum_check: bool = True, **kwargs
    ):
        """
        Downloads the file from cloud storage to local file.

        Args:
            src_file (str): Full path to the file in cloud storage.
            dst_file (str): Full path to the file to be downloaded.
            md5sum_check (bool): Option to check if the file has changed.
                Defaults to True.
            **kwargs: Additional keyword arguments to be forwarded to the 'get_bytes'
                method of the blob object.

        Example of using **kwargs:
            download_file(src_file, dst_file, start=10, end=50)
        """
        if md5sum_check and self.check_md5sum(src_file, dst_file):
            return None
        content_bytes = self.get_bytes(src_file, **kwargs)
        with open(dst_file, "wb") as f:
            f.write(content_bytes)
        return None

    def upload_file(
        self, local_file: str, gcs_file: str, md5sum_check: bool = True, **kwargs
    ):
        """
        Uploads a local file to google cloud storage.

        @param local_file (str): Full path to the local file.
        @param gcs_file (str): Full path to the bucket file.
        @param md5sum_check (bool): Option to check if the file has changed
            before uploading. Defaults to True.
        @param **kwargs: Additional keyword arguments to be forwarded to the
            'upload_from_filename' method of the blob object.

        For example, if the 'upload_from_filename' method accepts a 'content_type'
        argument, you can pass it like this:
        upload_file(local_file, gcs_file, content_type="text/csv")
        """
        if md5sum_check and self.check_md5sum(gcs_file, local_file):
            return None
        self.blob(gcs_file).upload_from_filename(local_file, **kwargs)
        return None

    def read_video(
        self, filepath: str, **kwargs
    ) -> Tuple[List[np.ndarray], Dict[str, Any]]:
        """
        Reads a video from a local file or remote file and returns a list of frames
        and metadata. It uses imageio and ffmpeg to decode the video.

        Args:
            filepath (str): Full path to the video file.
            **kwargs: Additional keyword arguments to be forwarded to the 'get_bytes'
                method if the file is on Google Cloud Storage.

        Returns:
            Tuple[List[np.ndarray], Dict[str, Any]]: List of frames and metadata.

        Example of using **kwargs:
            read_video(filepath, start=10, end=50)
        """
        if "gs://" in filepath:
            video_bytes = self.get_bytes(filepath, **kwargs)
        else:
            video_bytes = open(filepath, "rb").read()

        return decode_video(video_bytes)

    def read_video_gen(
        self, filepath: str
    ) -> Generator[Tuple[np.ndarray, Dict[str, Any]], None, None]:
        """! Reads a video from a local file or remote file and returns a list of
            frames and metadata. It uses imageio and ffmpeg to decode the video.
        @param filepath (str) Full path to the video file.
        @returns (Tuple[List[np.ndarray], Dict[str, Any]]) List of frames and metadata.
        """
        if "gs://" in filepath:
            video_bytes = self.get_bytes(filepath)
        else:
            video_bytes = open(filepath, "rb").read()

        return decode_video_gen(video_bytes)

    def write_video(
        self,
        dst_file: Union[str, BytesIO],
        frames: List[np.ndarray],
        fps: int = 30,
        format: str = "mp4",
        **kwargs,
    ):
        """! Writes a video to a local file, remote file or BytesIO object.
        For remote file only GCP storage is supported.
        @param dst_file (Union[str, BytesIO]) Path string or BytesIO object.
        @param frames (List[np.ndarray]) Video list of frames in RGB.
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

    def read_image(self, src_path: str, **kwargs) -> np.ndarray:
        """
        Reads an image from cloud or local storage and returns the image as a numpy array.

        Args:
            src_path (str): Full path to the image file.
            **kwargs: Additional keyword arguments to be forwarded to the
                'get_bytes' method if the file is on Google Cloud Storage.

        Returns:
            np.ndarray: Image as a numpy array.

        Example of using **kwargs:
            read_image(src_path, start=10, end=50)
        """
        if "gs://" in src_path:
            image_bytes = self.get_bytes(src_path, **kwargs)
        else:
            with open(src_path, "rb") as f:
                image_bytes = f.read()

        return iio.imread(image_bytes)

    def write_image(
        self,
        dst_file: str,
        image: np.ndarray,
        encode_args: Dict[str, str] = {},
        **kwargs,
    ):
        """
        Writes the image to the destination file locally or cloud.
        For the moment only GCP storage is supported.

        Args:
            dst_file (str): Full path to the image.
            image (np.ndarray): Image as numpy array.
            encode_args (Dict[str, str], optional): Encoding arguments.
            **kwargs: Additional keyword arguments to be forwarded to the
                'upload_data' method if the file is on Google Cloud Storage.

        Example of using **kwargs:
            write_image(dst_file, image, encode_args={"quality": 90}, custom_arg="value")
        """
        ext = Path(dst_file).suffix
        encoded_bytes = iio.imwrite("<bytes>", image, format=ext, **encode_args)

        if "gs://" in dst_file:
            content_type = self.extension_to_content_type[ext]
            self.upload_data(dst_file, encoded_bytes, content_type, **kwargs)
        else:
            with open(dst_file, "wb") as f:
                f.write(encoded_bytes)

    def list_dir(self, src_dir: str, delimiter=None) -> Iterator[str]:
        """Get the list of files/folders of a GCP directory recursively
        when no delimeter.

        Args:
            src_dir (str): GCP storeage directory
            delimiter ([str], optional): Delimeter. Defaults to None.

        Returns:
            Iterator[str]: List of files/folders in the directory.
        """
        bucket_name, file_path = get_bucket_and_path(src_dir)
        blobs = self.client.list_blobs(
            bucket_name, prefix=file_path, delimiter=delimiter
        )

        for blob in blobs:
            yield os.path.join("gs://", bucket_name, blob.name)


if __name__ == "__main__":
    pass
