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
from unittest.mock import patch
from tests.recipes.recipe_ctx import RecipeCtx


class TestGeventRecipe(RecipeCtx, unittest.TestCase):

    recipe_name = "gevent"

    def test_get_recipe_env(self):
        """
        Makes sure `get_recipe_env()` sets compilation flags properly.
        """
        mocked_cflags = (
            '-DANDROID -fomit-frame-pointer -D__ANDROID_API__=27 -mandroid '
            '-isystem /path/to/isystem '
            '-I/path/to/include1 '
            '-isysroot /path/to/sysroot '
            '-I/path/to/include2 '
            '-march=armv7-a -mfloat-abi=softfp -mfpu=vfp -mthumb '
            '-I/path/to/python3-libffi-openssl/include'
        )
        mocked_ldflags = (
            ' --sysroot /path/to/sysroot '
            '-lm '
            '-L/path/to/library1 '
            '-L/path/to/library2 '
            '-lpython3.7m '
            # checks the regex doesn't parse `python3-libffi-openssl` as a `-libffi`
            '-L/path/to/python3-libffi-openssl/library3 '
        )
        mocked_ldlibs = ' -lm'
        mocked_env = {
            'CFLAGS': mocked_cflags,
            'LDFLAGS': mocked_ldflags,
            'LDLIBS': mocked_ldlibs,
        }
        with patch('pythonforandroid.recipe.CythonRecipe.get_recipe_env') as m_get_recipe_env:
            m_get_recipe_env.return_value = mocked_env
            env = self.recipe.get_recipe_env()
        expected_cflags = (
            ' -fomit-frame-pointer -mandroid -isystem /path/to/isystem'
            ' -isysroot /path/to/sysroot'
            ' -march=armv7-a -mfloat-abi=softfp -mfpu=vfp -mthumb'
        )
        expected_cppflags = (
            '-DANDROID -D__ANDROID_API__=27 '
            '-I/path/to/include1 '
            '-I/path/to/include2 '
            '-I/path/to/python3-libffi-openssl/include'
        )
        expected_ldflags = (
            ' --sysroot /path/to/sysroot'
            ' -L/path/to/library1'
            ' -L/path/to/library2'
            ' -L/path/to/python3-libffi-openssl/library3 '
        )
        expected_ldlibs = mocked_ldlibs
        expected_libs = '-lm -lpython3.7m -lm'
        expected_env = {
            'CFLAGS': expected_cflags,
            'CPPFLAGS': expected_cppflags,
            'LDFLAGS': expected_ldflags,
            'LDLIBS': expected_ldlibs,
            'LIBS': expected_libs,
        }
        self.assertEqual(expected_env, env)
