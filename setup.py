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
    # --- ENSURE THESE ARE LISTED ---
    install_requires=[
        "questionary",
        "click",
        "rich"
    ],
    # -------------------------------
    entry_points={
        'console_scripts': [
            'neuro=neuro.cli:main',
        ],
    },
)
