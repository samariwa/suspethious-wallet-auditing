#!/usr/bin/python3
from setuptools import setup

setup(
    use_scm_version={
        "fallback_version": "1.0.0",
        "write_to": "eth_wallet/_version.py",
        "write_to_template": "__version__ = {version!r}",
    }
)
