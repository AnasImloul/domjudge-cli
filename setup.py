from setuptools import setup, find_packages

setup(
    name="dom-cli",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "pyyaml",
        "typer",
    ],
    entry_points={
        "console_scripts": [
            "dom=dom.cli:app",
        ],
    },
)
