#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""setup.py for nixmcp."""

from setuptools import setup

if __name__ == "__main__":
    setup(
        install_requires=[
            "mcp>=1.5.0",
            "requests>=2.32.3",
            "python-dotenv>=1.1.0",
            "beautifulsoup4>=4.13.3",
        ],
    )
