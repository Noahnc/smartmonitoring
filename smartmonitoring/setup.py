from setuptools import setup, find_packages
from smartmonitoring import __version__

setup(
    name='smartmonitoring',
    description='A Tool to deploy and update SmartMonitoring Proxies',
    version=__version__,
    packages=find_packages(
        where='.',
        include=['smartmonitoring*']
    ),
    install_requires=[
        'requests',
        'click',
        'docker',
        'packaging',
        'cerberus',
        'rich',
        'pyfiglet',
        'termcolor',
        'deepdiff',
        'psutil'
    ],
    python_requires='>=3.9',
    entry_points='''
        [console_scripts]
        smartmonitoring=smartmonitoring.__main__:main
    ''',
    author="Noah Canadea",
    url='https://github.com/Noahnc/smartmonitoring',
    download_url='https://github.com/CITGuru/cver/archive/1.0.0.tar.gz',
    author_email='noah@canadea.ch'
)
