from setuptools import setup, find_packages
from pathlib import Path

# read requirements.txt, strip comments and blank lines
req_path = Path(__file__).parent / "requirements.txt"
install_requires = [
    line.strip()
    for line in req_path.read_text().splitlines()
    if line.strip() and not line.strip().startswith("#")
]

setup(
    name="domjudge-cli",
    version="0.2.9",
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "dom=dom.cli.__init__:main",
        ],
    },
)
