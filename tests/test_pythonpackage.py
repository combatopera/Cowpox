# Copyright 2020 Andrzej Cichocki

# This file is part of Cowpox.
#
# Cowpox is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Cowpox is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Cowpox.  If not, see <http://www.gnu.org/licenses/>.

# This file incorporates work covered by the following copyright and
# permission notice:

# Copyright (c) 2010-2017 Kivy Team and other contributors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
THESE TESTS DON'T RUN IN TRAVIS (takes too long!!)
ONLY THE BASIC ONES IN test_pythonpackage_basic.py DO.

(This file basically covers all tests for any of the
functions that aren't already part of the basic
test set)
"""

import os
import shutil
import tempfile

from pythonforandroid.pythonpackage import (
    _extract_info_from_package,
    extract_metainfo_files_from_package,
    get_package_as_folder,
    get_package_dependencies,
)


def local_repo_folder():
    return os.path.abspath(os.path.join(
        os.path.dirname(__file__), ".."
    ))


def test_get_package_dependencies():
    # TEST 1 from source code folder:
    deps_nonrecursive = get_package_dependencies(
        local_repo_folder(), recursive=False
    )
    deps_recursive = get_package_dependencies(
        local_repo_folder(), recursive=True
    )
    # Check that jinja2 is returned as direct dep:
    assert len([dep for dep in deps_nonrecursive
                if "jinja2" in dep]) > 0
    # Check that MarkupSafe is returned as indirect dep of jinja2:
    assert [
        dep for dep in deps_recursive
        if "MarkupSafe" in dep
    ]
    # Check setuptools not being in non-recursive deps:
    # (It will be in recursive ones due to p4a's pep517 dependency)
    assert "setuptools" not in deps_nonrecursive
    # Check setuptools is present in non-recursive deps,
    # if we also add build requirements:
    assert "setuptools" in get_package_dependencies(
        local_repo_folder(), recursive=False,
        include_build_requirements=True,
    )

    # TEST 2 from external ref:
    # Check that jinja2 is returned as direct dep:
    assert len([dep for dep in get_package_dependencies("python-for-android")
                if "jinja2" in dep]) > 0
    # Check that MarkupSafe is returned as indirect dep of jinja2:
    assert [
        dep for dep in get_package_dependencies(
            "python-for-android", recursive=True
        )
        if "MarkupSafe" in dep
    ]


def test_extract_metainfo_files_from_package():
    # TEST 1 from external ref:
    files_dir = tempfile.mkdtemp()
    try:
        extract_metainfo_files_from_package("python-for-android",
                                            files_dir, debug=True)
        assert os.path.exists(os.path.join(files_dir, "METADATA"))
    finally:
        shutil.rmtree(files_dir)

    # TEST 2 from local folder:
    files_dir = tempfile.mkdtemp()
    try:
        extract_metainfo_files_from_package(local_repo_folder(),
                                            files_dir, debug=True)
        assert os.path.exists(os.path.join(files_dir, "METADATA"))
    finally:
        shutil.rmtree(files_dir)


def test_get_package_as_folder():
    # WARNING !!! This function behaves DIFFERENTLY if the requested package
    # has a wheel available vs a source package. What we're getting is
    # essentially what pip also would fetch, but this can obviously CHANGE
    # depending on what is happening/available on PyPI.
    #
    # Therefore, this test doesn't really go in-depth.
    (obtained_type, obtained_path) = \
        get_package_as_folder("python-for-android")
    try:
        assert obtained_type in {"source", "wheel"}
        assert os.path.isdir(obtained_path)
    finally:
        # Try to ensure cleanup:
        shutil.rmtree(obtained_path)


def test__extract_info_from_package():
    # This is indirectly already tested a lot through get_package_name()
    # and get_package_dependencies(), so we'll just do one basic test:

    assert _extract_info_from_package(
        local_repo_folder(),
        extract_type="name"
    ) == "python-for-android"
