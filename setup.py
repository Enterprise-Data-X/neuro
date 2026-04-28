from setuptools import setup, find_packages

packages = ["neuro"] + [f"neuro.{pkg}" for pkg in find_packages(where="src")]

setup(
    name="neuro",
    version="0.1.0",
    package_dir={"neuro": "src"},
    packages=packages,
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'neuro=neuro.cli:main',
        ],
    },
)