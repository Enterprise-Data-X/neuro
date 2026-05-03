from setuptools import setup, find_packages

setup(
    name="neuro",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    package_data={
        'neuro': ['NEURO.md'],
    },
    include_package_data=True,
    install_requires=[
        "click",
        "rich",
        "prompt_toolkit",
    ],
    extras_require={
        "anthropic": ["anthropic"],
        "openai":    ["openai"],
        "github":    ["openai"],
        "all":       ["anthropic", "openai"],
    },
    entry_points={
        'console_scripts': [
            'neuro=neuro.cli:main',
        ],
    },
)
