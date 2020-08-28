import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="verification",
    version="0.0.1",
    author="Amy Fang",
    author_email="axf4@cornell.edu",
    description="Verification",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/CREATE-knowledge-planning/Verification",
    packages=setuptools.find_packages(),
    python_requires='>=3.7',
)