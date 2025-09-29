from setuptools import setup, find_packages

setup(
    name="unified-intelligence-cli",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=open("requirements.txt").readlines(),
    entry_points={"console_scripts": ["uicli = main:main"]},  # CLI entry
)