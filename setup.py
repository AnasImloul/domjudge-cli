from setuptools import setup, find_packages

setup(
    name="domjudge-cli",
    version="0.1.4",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "typer~=0.15.2",
        "PyYAML~=6.0.2",
        "pydantic~=2.11.3",
        "pydantic[email]~=2.11.3",
        "p2d~=0.3.0",
        "bcrypt~=4.3.0",
        "webcolors~=24.11.1",
        "requests~=2.32.3",
        "Jinja2~=3.1.6",
    ],
    entry_points={
        "console_scripts": [
            "dom=dom.cli.__main__:main",
        ],
    },
)
