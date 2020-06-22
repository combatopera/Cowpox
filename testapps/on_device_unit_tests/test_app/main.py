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

import sys
if sys.version_info.major < 3:
    print(('Running under Python {} but these tests '
           'require Python 3+').format(sys.version_info.major))

import unittest
import importlib

print('Imported unittest')


class PythonTestMixIn(object):

    module_import = None

    def test_import_module(self):
        """Test importing the specified Python module name. This import test
        is common to all Python modules, it does not test any further
        functionality.
        """
        self.assertIsNotNone(
            self.module_import,
            'module_import is not set (was default None)')

        importlib.import_module(self.module_import)

    def test_run_module(self):
        """Import the specified module and do something with it as a minimal
        check that it actually works.

        This test fails by default, it must be overridden by every
        child test class.
        """

        self.fail('This test must be overridden by {}'.format(self))

print('Defined test case')

import sys
sys.path.append('./')
from tests import test_requirements
suite = unittest.TestLoader().loadTestsFromModule(test_requirements)
unittest.TextTestRunner().run(suite)

print('Ran tests')
