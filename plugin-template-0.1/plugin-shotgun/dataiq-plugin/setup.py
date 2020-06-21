# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
import setuptools

with open("README.md") as fp:
    long_description = fp.read()

setuptools.setup(
    name="dataiq-plugin",
    version="0.11.1",
    author="Example",
    author_email="example",
    description="Package for building DataIQ plugins",
    long_description=long_description,
    url="NA",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.6"
)
