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
from tests.recipes.recipe_ctx import RecipeCtx
from pythonforandroid.recipe import Recipe


class TestPyIcuRecipe(RecipeCtx, unittest.TestCase):
    """
    An unittest for recipe :mod:`~pythonforandroid.recipes.pyicu`
    """
    recipe_name = "pyicu"

    @mock.patch("pythonforandroid.recipe.Recipe.check_recipe_choices")
    @mock.patch("pythonforandroid.build.ensure_dir")
    @mock.patch("pythonforandroid.archs.glob")
    @mock.patch("pythonforandroid.archs.find_executable")
    def test_get_recipe_env(
        self,
        mock_find_executable,
        mock_glob,
        mock_ensure_dir,
        mock_check_recipe_choices,
    ):
        """
        Test that method
        :meth:`~pythonforandroid.recipes.pyicu.PyICURecipe.get_recipe_env`
        returns the expected flags
        """
        icu_recipe = Recipe.get_recipe("icu", self.ctx)

        mock_find_executable.return_value = (
            "/opt/android/android-ndk/toolchains/"
            "llvm/prebuilt/linux-x86_64/bin/clang"
        )
        mock_glob.return_value = ["llvm"]
        mock_check_recipe_choices.return_value = sorted(
            self.ctx.recipe_build_order
        )

        expected_pyicu_libs = [
            lib[3:-3] for lib in icu_recipe.built_libraries.keys()
        ]
        env = self.recipe.get_recipe_env(self.arch)
        self.assertEqual(":".join(expected_pyicu_libs), env["PYICU_LIBRARIES"])
        self.assertIn("include/icu", env["CPPFLAGS"])
        self.assertIn("icu4c/icu_build/lib", env["LDFLAGS"])

        # make sure that the mocked methods are actually called
        mock_glob.assert_called()
        mock_ensure_dir.assert_called()
        mock_find_executable.assert_called()
        mock_check_recipe_choices.assert_called()
