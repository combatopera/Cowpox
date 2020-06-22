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

import unittest
from unittest import mock
from tests.recipes.recipe_lib_test import BaseTestForCmakeRecipe


class TestOpenalRecipe(BaseTestForCmakeRecipe, unittest.TestCase):
    """
    An unittest for recipe :mod:`~pythonforandroid.recipes.openal`
    """
    recipe_name = "openal"

    @mock.patch("pythonforandroid.recipes.openal.sh.cmake")
    @mock.patch("pythonforandroid.recipes.openal.sh.make")
    @mock.patch("pythonforandroid.recipes.openal.sh.cp")
    @mock.patch("pythonforandroid.util.chdir")
    @mock.patch("pythonforandroid.build.ensure_dir")
    @mock.patch("pythonforandroid.archs.glob")
    @mock.patch("pythonforandroid.archs.find_executable")
    def test_prebuild_arch(
        self,
        mock_find_executable,
        mock_glob,
        mock_ensure_dir,
        mock_current_directory,
        mock_sh_cp,
        mock_sh_make,
        mock_sh_cmake,
    ):
        mock_find_executable.return_value = (
            "/opt/android/android-ndk/toolchains/"
            "llvm/prebuilt/linux-x86_64/bin/clang"
        )
        mock_glob.return_value = ["llvm"]
        self.recipe.build_arch(self.arch)

        # make sure that the mocked methods are actually called
        mock_glob.assert_called()
        mock_ensure_dir.assert_called()
        mock_current_directory.assert_called()
        mock_find_executable.assert_called()
        mock_sh_cp.assert_called()
        mock_sh_make.assert_called()
        mock_sh_cmake.assert_called()

    @mock.patch("pythonforandroid.recipes.openal.sh.cp")
    @mock.patch("pythonforandroid.util.chdir")
    @mock.patch("pythonforandroid.build.ensure_dir")
    @mock.patch("pythonforandroid.archs.glob")
    @mock.patch("pythonforandroid.archs.find_executable")
    def test_build_arch(
        self,
        mock_find_executable,
        mock_glob,
        mock_ensure_dir,
        mock_current_directory,
        mock_sh_cp,
    ):
        # We overwrite the base test method because we need to mock a little
        # more with this recipe (`sh.cp` and `sh.rm`)
        super().test_build_arch()
        # make sure that the mocked methods are actually called
        mock_sh_cp.assert_called()
