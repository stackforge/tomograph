#!/usr/bin/env python

import setuptools


def read_requires():
    requires = []
    with open('tools/pip-requires', 'r') as fh:
        contents = fh.read()
        for line in contents.splitlines():
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            try:
                (line, after) = line.split("#", 1)
            except ValueError:
                pass
            if not line:
                continue
            requires.append(line)
    return requires


setuptools.setup(
    name='tomograph',
    version="0.0.1",
    description='Tiny tims tracing tomograph',
    author="Y! OpenStack Team",
    author_email='timjr@yahoo-inc.com',
    license='Apache License, Version 2.0',
    packages=setuptools.find_packages(),
    long_description=open('README.md').read(),
    install_requires=read_requires(),
)