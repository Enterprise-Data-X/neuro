from setuptools import setup, find_packages

setup(
    name="neuro",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'neuro=neuro.cli:main',
        ],
    },
)