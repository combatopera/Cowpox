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
from os.path import join
from tests.recipes.recipe_lib_test import BaseTestForMakeRecipe


class TestLibLzmaRecipe(BaseTestForMakeRecipe, unittest.TestCase):
    """TestCase for recipe :mod:`~pythonforandroid.recipes.liblzma`."""
    recipe_name = "liblzma"
    sh_command_calls = ["./autogen.sh", "autoreconf", "./configure"]

    def test_get_library_includes(self):
        """
        Test :meth:`~pythonforandroid.recipes.liblzma.get_library_includes`.
        """
        recipe_build_dir = self.recipe.get_build_dir(self.arch.arch)
        self.assertEqual(
            self.recipe.get_library_includes(self.arch),
            f" -I{join(recipe_build_dir, 'install/include')}",
        )

    def test_get_library_ldflags(self):
        """
        Test :meth:`~pythonforandroid.recipes.liblzma.get_library_ldflags`.
        """
        recipe_build_dir = self.recipe.get_build_dir(self.arch.arch)
        self.assertEqual(
            self.recipe.get_library_ldflags(self.arch),
            f" -L{join(recipe_build_dir, 'install/lib')}",
        )

    def test_link_libs_flags(self):
        """
        Test :meth:`~pythonforandroid.recipes.liblzma.get_library_libs_flag`.
        """
        self.assertEqual(self.recipe.get_library_libs_flag(), " -llzma")
