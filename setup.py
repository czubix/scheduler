from setuptools import setup, find_packages

with open("README.md", "r") as file:
    readme = file.read()

setup(
    name = "scheduler",
    version = "0.1.0",
    author = "czubix",
    description = "A simple async scheduler library",
    license = "Apache 2.0",
    long_description = readme,
    long_description_content_type = "text/markdown",
    url = "https://github.com/czubix/scheduler",
    packages = find_packages(exclude=["docs"])
)