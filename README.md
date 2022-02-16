# gcp-io

[![codecov](https://codecov.io/gh/kiwicampus/gcp-io/branch/main/graph/badge.svg?token=BBO872LDKQ)](https://codecov.io/gh/kiwicampus/gcp-io)

This library provides an easy interface to do some common I/O tasks on Google Cloud Storage (GCS). Those include:

* Reading/writing an image file from and to GCS.
* Reading/writing a video file from and to GCS.
* Reading/writing a yaml file from and to GCS.
* Uploading/downloading a file from and to GCS.
* Checking md5 checksum of a file.
* Checking if a file exists in GCS.
* Listing directories in GCS.

## Installation
```
pip install git+https://github.com/kiwicampus/gcp-io.git@main
```

or with poetry

```
poetry add git+https://github.com/kiwicampus/gcp-io.git@main
```

## Usage

```python
from gcp_io import GCPInterface

# this will try to load credentials from environment variable 
# GOOGLE_APPLICATION_CREDENTIALS or from gsutil if installed
interface = GCPInterface()

# this will try to load credentials from a .json file
interface = GCPInterface("/key/to/credentials.json")

# this will be authenticated directly using a storage.Client object
from google.cloud import storage
interface = GCPInterface(storage.Client())

# Use its methods comfortably
image = interface.read_image("gs://bucket/path/to/image.jpg")
interface.write_image("gs://bucket/path/to/image.jpg", image)
```
