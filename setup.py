#!/bin/env python
import os

from setuptools import setup


def find_xdg_data_files(syspath, relativepath, pkgname, data_files=[]):
    for (dirname, _, filenames) in os.walk(relativepath):
        if filenames:
            syspath = syspath.format(pkgname=pkgname)

            subpath = dirname.split(relativepath)[1]
            if subpath.startswith("/"):
                subpath = subpath[1:]

            files = [os.path.join(dirname, f) for f in filenames]
            data_files.append((os.path.join(syspath, subpath), files))

    return data_files


def find_data_files(data_map, pkgname):
    data_files = []

    for (syspath, relativepath) in data_map:
        find_xdg_data_files(syspath, relativepath, pkgname, data_files)

    return data_files


DATA_FILES = [
    ("share/{pkgname}/plugins", "data/plugins"),
    ("share/icons", "data/icons"),
]


setup(
    author="Elio Esteves Duarte",
    author_email="elio.esteves.duarte@gmail.com",
    description="Shows a fulls creen window which prevents users from using the computer during a break",
    include_package_data=True,
    keywords="pomodoro,tomate",
    license="GNU General Public License v2.0",
    long_description=open("README.md").read(),
    name="tomate-breakscreen-plugin",
    data_files=find_data_files(DATA_FILES, "tomate"),
    url="https://github.com/eliostva/tomate-breakscreen-plugin",
    version="0.6.1",
    zip_safe=False,
    py_modules=[],
)
