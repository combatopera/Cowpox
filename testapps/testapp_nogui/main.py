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


from math import sqrt
print('import math worked')

import sys

print('sys.path is', sys.path)

for i in range(45, 50):
    print(i, sqrt(i))

print('trying to import six')
try:
    import six
except ImportError:
    print('import failed')


print('trying to import six again')
try:
    import six
except ImportError:
    print('import failed (again?)')
print('import six worked!')

print('Just printing stuff apparently worked, trying pyjnius')

import jnius

print('Importing jnius worked')

print('trying to import stuff')

try:
    from jnius import cast
except ImportError:
    print('cast failed')

try:
    from jnius import ensureclass
except ImportError:
    print('ensureclass failed')

try:
    from jnius import JavaClass
except ImportError:
    print('JavaClass failed')

try:
    from jnius import jnius
except ImportError:
    print('jnius failed')

try:
    from jnius import reflect
except ImportError:
    print('reflect failed')

try:
    from jnius import find_javaclass
except ImportError:
    print('find_javaclass failed')

print('Trying to autoclass activity')

from jnius import autoclass

print('Imported autoclass')

PythonActivity = autoclass('org.kivy.android.PythonActivity')

print(':o the autoclass worked!')

