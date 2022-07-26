from setuptools import setup, find_packages
from io import open
from os import path
import pathlib


setup(
    name='smartmonitoring',
    description='A Tool to deploy and update SmartMonitoring Proxies',
    version='1.0.0',
    packages = {'smartmonitoring'},
    install_requires=[
        'requests',
        'click',
        'docker',
        'packaging',
        'cerberus',
        'prettytable',
        'pyfiglet',
        'termcolor',
        'deepdiff',
    ],
    python_requires='>=3.9',
    entry_points='''
        [console_scripts]
        smartmonitoring=smartmonitoring.__main__:cli
    ''',
    author="Noah Canadea",
    url='https://github.com/Noahnc/smartmonitoring',
    download_url='https://github.com/CITGuru/cver/archive/1.0.0.tar.gz',
    author_email='noah@canadea.ch',
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ]
)
