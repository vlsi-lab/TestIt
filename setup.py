from setuptools import setup, find_packages

with open("README.md", "r", encoding = "utf-8") as fh:
    long_description = fh.read()

setup(
    name="verifit",
    version="0.1",
    author="Tommaso Terzano",
    author_email="tommaso.terzano@gmail.com",
    description="A tool for verifying FPGA models using custom SW applications",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    package_dir = {"": "src"},
    include_package_data=True,
    package_data={
        "verifit": ["templates/*"], 
    },
    packages=find_packages(where="src"),
    install_requires=[
        "rich",
        "pexpect",
        "numpy",
        "pyserial",
        "hjson",
        "importlib_resources"
    ],
    entry_points={
        "console_scripts": [
            "verifit=verifit.main:main",
        ],
    },
    python_requires = ">=3.7"
)