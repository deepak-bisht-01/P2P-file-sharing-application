from setuptools import setup, find_packages

setup(
    name="p2p-messaging",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "cryptography>=41.0.0",
        "pyyaml>=6.0",
        "colorama>=0.4.6",
        "click>=8.1.0",
    ],
    entry_points={
        "console_scripts": [
            "p2p-chat=cli.interface:main",
        ],
    },
    python_requires=">=3.8",
)