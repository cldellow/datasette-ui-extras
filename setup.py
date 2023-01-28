from setuptools import setup
import os

VERSION = "0.8"


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="datasette-ui-extras",
    description="Adds UI enhancements to Datasette",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Colin Dellow",
    url="https://github.com/cldellow/datasette-ui-extras",
    project_urls={
        "Issues": "https://github.com/cldellow/datasette-ui-extras/issues",
        "CI": "https://github.com/cldellow/datasette-ui-extras/actions",
        "Changelog": "https://github.com/cldellow/datasette-ui-extras/releases",
    },
    license="Apache License, Version 2.0",
    classifiers=[
        "Framework :: Datasette",
        "License :: OSI Approved :: Apache Software License"
    ],
    version=VERSION,
    packages=["datasette_ui_extras"],
    entry_points={"datasette": ["ui_extras = datasette_ui_extras"]},
    install_requires=["datasette"],
    extras_require={"test": ["pytest", "pytest-asyncio", "pytest-watch", "sqlite-utils"]},
    package_data={
        "datasette_ui_extras": ["static/*", "templates/*"]
    },
    python_requires=">=3.7",
)
