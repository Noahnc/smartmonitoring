from setuptools import setup, find_packages
from smartmonitoring_cli import __version__

setup(
    name='smartmonitoring_cli',
    description='A Tool to deploy and update SmartMonitoring Deployments',
    version=__version__,
    packages=find_packages(
        where='.',
        include=['smartmonitoring_cli*']
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
        'psutil',
    ],
    python_requires='>=3.10',
    entry_points='''
        [console_scripts]
        smartmonitoring=smartmonitoring_cli.__main__:main
    ''',
    author="Noah Canadea",
    url='https://github.com/Noahnc/smartmonitoring',
    author_email='noah@canadea.ch'
)
