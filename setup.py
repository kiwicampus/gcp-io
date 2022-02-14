from setuptools import setup, find_packages


with open("README.md", "r") as readme:
    setup(
        name="gcp_io",
        version="0.0.1",
        author="Carlos Alvarez",
        author_email="carlos.alvarez@kiwibot.com",
        description="GCP io utilities",
        long_description=readme.read(),
        license="MIT",
        keywords=[],
        url="https://github.com/kiwicampus/gcp-io",
        packages=find_packages(),
        package_data={},
        include_package_data=True,
        install_requires=[
            "numpy",
            "pyyaml",
            "google-cloud-storage",
            # "opencv-python-headless",
            "imageio<=2.10.0",
            "imageio-ffmpeg<=0.4.0",
        ],
    )
