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

import os
import unittest
from unittest.mock import patch
from tests.recipes.recipe_ctx import RecipeCtx
from pythonforandroid.util import ensure_dir


class TestReportLabRecipe(RecipeCtx, unittest.TestCase):
    recipe_name = "reportlab"

    def setUp(self):
        """
        Setups recipe and context.
        """
        super().setUp()
        self.recipe_dir = self.recipe.get_build_dir(self.arch.arch)
        ensure_dir(self.recipe_dir)

    def test_prebuild_arch(self):
        """
        Makes sure `prebuild_arch()` runs without error and patches `setup.py`
        as expected.
        """
        # `prebuild_arch()` dynamically replaces strings in the `setup.py` file
        setup_path = os.path.join(self.recipe_dir, 'setup.py')
        with open(setup_path, 'w') as setup_file:
            setup_file.write('_FT_LIB_\n')
            setup_file.write('_FT_INC_\n')

        # these sh commands are not relevant for the test and need to be mocked
        with \
                patch('sh.patch'), \
                patch('sh.touch'), \
                patch('sh.unzip'), \
                patch('os.path.isfile'):
            self.recipe.prebuild_arch(self.arch)
        # makes sure placeholder got replaced with library and include paths
        with open(setup_path, 'r') as setup_file:
            lines = setup_file.readlines()
        self.assertTrue(lines[0].endswith('freetype/objs/.libs\n'))
        self.assertTrue(lines[1].endswith('freetype/include\n'))
