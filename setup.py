#!/usr/bin/env python
# coding: utf8

import os

from setuptools import find_packages, setup


def setup_package():
    setup(
        name="ac_aqd",
        version="0.0.0",
        description="Streamlit app for ac-aqd.",
        author="King Chung Huang",
        author_email="kinghuang@mac.com",
        packages=find_packages(),
        include_package_data=True,
        install_requires=[
            "streamlit",
        ],
        dependency_links=[

        ],
        zip_safe=True,
    )


if __name__ == "__main__":
    setup_package()
