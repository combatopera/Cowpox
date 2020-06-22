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

from enum import Enum


class TargetPython(Enum):
    python2 = 0
    python3 = 2


# recipes that currently break the build
# a recipe could be broken for a target Python and not for the other,
# hence we're maintaining one list per Python target
BROKEN_RECIPES_PYTHON2 = set([
    # pythonhelpers.h:12:18: fatal error: string: No such file or directory
    'atom',
    # https://github.com/kivy/python-for-android/issues/550
    'audiostream',
    'brokenrecipe',
    'evdev',
    # distutils.errors.DistutilsError
    # Could not find suitable distribution for Requirement.parse('cython')
    'ffpyplayer',
    'flask',
    'groestlcoin_hash',
    # https://github.com/kivy/python-for-android/issues/1354
    'kiwisolver',
    'libmysqlclient',
    'libsecp256k1',
    'libtribler',
    'ndghttpsclient',
    'm2crypto',
    # ImportError: No module named setuptools
    'netifaces',
    'Pillow',
    # depends on cffi that still seems to have compilation issues
    'protobuf_cpp',
    'xeddsa',
    'x3dh',
    'pynacl',
    'doubleratchet',
    'omemo',
    # requires `libpq-dev` system dependency e.g. for `pg_config` binary
    'psycopg2',
    # most likely some setup in the Docker container, because it works in host
    'pyjnius', 'pyopenal',
    'pyproj',
    'pysdl2',
    'pyzmq',
    'secp256k1',
    'shapely',
    # mpmath package with a version >= 0.19 required
    'sympy',
    'twisted',
    'vlc',
    'websocket-client',
    'zeroconf',
    'zope',
])
BROKEN_RECIPES_PYTHON3 = set([
    'brokenrecipe',
    # enum34 is not compatible with Python 3.6 standard library
    # https://stackoverflow.com/a/45716067/185510
    'enum34',
    # build_dir = glob.glob('build/lib.*')[0]
    # IndexError: list index out of range
    'secp256k1',
    'ffpyplayer',
    # requires `libpq-dev` system dependency e.g. for `pg_config` binary
    'psycopg2',
    # most likely some setup in the Docker container, because it works in host
    'pyjnius', 'pyopenal',
    # SyntaxError: invalid syntax (Python2)
    'storm',
    # mpmath package with a version >= 0.19 required
    'sympy',
    'vlc',
])

BROKEN_RECIPES = {
    TargetPython.python2: BROKEN_RECIPES_PYTHON2,
    TargetPython.python3: BROKEN_RECIPES_PYTHON3,
}
# recipes that were already built will be skipped
CORE_RECIPES = set([
    'pyjnius', 'kivy', 'openssl', 'requests', 'sqlite3', 'setuptools',
    'numpy', 'android', 'hostpython2', 'hostpython3', 'python2', 'python3',
])
