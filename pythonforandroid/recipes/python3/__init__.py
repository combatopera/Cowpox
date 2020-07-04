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

from cowpox.python import GuestPythonRecipe
from lagoon.program import Program
import lagoon

class Python3Recipe(GuestPythonRecipe):

    version = '3.8.1' # XXX: Should this match container version?
    url = f"https://www.python.org/ftp/python/{version}/Python-{version}.tgz"
    depends = ['sqlite3', 'openssl', 'libffi']
    opt_depends = ['libbz2', 'liblzma']

    def mainbuild(self):
        self.apply_patch('py3.8.1.patch')
        if hasattr(lagoon, 'lld'):
            self.apply_patch('py3.8.1_fix_cortex_a8.patch')
        configure_args = [
            f"--host={self.arch.command_prefix}",
            f"--build={Program.text(self.recipebuilddir / 'config.guess')().rstrip()}",
            '--enable-shared',
            '--enable-ipv6',
            'ac_cv_file__dev_ptmx=yes',
            'ac_cv_file__dev_ptc=no',
            '--without-ensurepip',
            'ac_cv_little_endian_double=yes',
            '--prefix=/usr/local',
            '--exec-prefix=/usr/local',
        ]
        if 'openssl' in self.graphinfo.recipenames:
            configure_args += [f"--with-openssl={self.graph.get_recipe('openssl').recipebuilddir}"]
        self.build_android(configure_args)
