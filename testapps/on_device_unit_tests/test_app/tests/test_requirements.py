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


from main import PythonTestMixIn
from unittest import TestCase


class NumpyTestCase(PythonTestMixIn, TestCase):
    module_import = 'numpy'

    def test_run_module(self):
        import numpy as np

        arr = np.random.random((3, 3))
        det = np.linalg.det(arr)


class OpensslTestCase(PythonTestMixIn, TestCase):
    module_import = '_ssl'

    def test_run_module(self):
        import ssl

        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.options &= ~ssl.OP_NO_SSLv3
        

class SqliteTestCase(PythonTestMixIn, TestCase):
    module_import = 'sqlite3'

    def test_run_module(self):
        import sqlite3

        conn = sqlite3.connect('example.db')
        conn.cursor()
        

class KivyTestCase(PythonTestMixIn, TestCase):
    module_import = 'kivy'

    def test_run_module(self):
        # This import has side effects, if it works then it's an
        # indication that Kivy is okay
        from kivy.core.window import Window


class PyjniusTestCase(PythonTestMixIn, TestCase):
    module_import = 'jnius'

    def test_run_module(self):
        from jnius import autoclass
        autoclass('org.kivy.android.PythonActivity')
