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

from cowpox.patch import version_starts_with
from p4a.python import GuestPythonRecipe
import lagoon

class Python3Recipe(GuestPythonRecipe):

    version = '3.8.1'
    urlformat = "https://www.python.org/ftp/python/{version}/Python-{version}.tgz"
    patches = [
        version_starts_with('3.7', 'py3.7.1_fix-ctypes-util-find-library.patch'),
        version_starts_with('3.7', 'py3.7.1_fix-zlib-version.patch'),
        version_starts_with('3.8', 'py3.8.1.patch'),
    ]
    if hasattr(lagoon, 'lld'):
        patches += [
            version_starts_with('3.7', 'py3.7.1_fix_cortex_a8.patch'),
            version_starts_with('3.8', 'py3.8.1_fix_cortex_a8.patch'),
        ]
    depends = ['hostpython3', 'sqlite3', 'openssl', 'libffi']
    opt_depends = ['libbz2', 'liblzma']
    conflicts = ['python2']
    configure_args = (
        '--host={android_host}',
        '--build={android_build}',
        '--enable-shared',
        '--enable-ipv6',
        'ac_cv_file__dev_ptmx=yes',
        'ac_cv_file__dev_ptc=no',
        '--without-ensurepip',
        'ac_cv_little_endian_double=yes',
        '--prefix={prefix}',
        '--exec-prefix={exec_prefix}',
    )

    def set_libs_flags(self, env):
        if 'openssl' in self.graphinfo.recipenames:
            self.configure_args += (f"--with-openssl={self.graph.get_recipe('openssl').get_build_dir()}",)
        return super().set_libs_flags(env)
