import setuptools
import py2exe

with open("requirements.txt") as fp:
    requirements = fp.read().splitlines()

setuptools.setup(
    name="gscanner",
    author="h0nda",
    url="https://github.com/h0nde/roblox-group-scanner-v2",
    packages=setuptools.find_packages(),
    classifiers=[],
    install_requires=requirements,
    options={"py2exe": {"bundle_files": 1, "compressed": True}},
    console=["scanner.py"]
)