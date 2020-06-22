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

from os.path import exists, join
from multiprocessing import cpu_count
from pythonforandroid.recipe import Recipe
from pythonforandroid.logger import shprint
from pythonforandroid.util import current_directory
import sh


class LibffiRecipe(Recipe):
    """
    Requires additional system dependencies on Ubuntu:
        - `automake` for the `aclocal` binary
        - `autoconf` for the `autoreconf` binary
        - `libltdl-dev` which defines the `LT_SYS_SYMBOL_USCORE` macro

    .. note::
        Some notes about libffi version:

            - v3.2.1 it's from year 2014...it's a little outdated and has
              problems with clang (see issue #1525)
            - v3.3-rc0 it was released at april 2018 (it's a pre-release), and
              it lacks some commits that we are interested, specially those
              ones that fixes specific issues for Arm64, you can check those
              commits at (search for commit `8fa8837` and look at the below
              commits): https://github.com/libffi/libffi/commits/master
    """
    name = 'libffi'
    # Version pinned to post `v3.3RC0`
    version = '8fa8837'
    url = 'https://github.com/libffi/libffi/archive/{version}.tar.gz'

    patches = ['remove-version-info.patch']

    built_libraries = {'libffi.so': '.libs'}

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            if not exists('configure'):
                shprint(sh.Command('./autogen.sh'), _env=env)
            shprint(sh.Command('autoreconf'), '-vif', _env=env)
            shprint(sh.Command('./configure'),
                    '--host=' + arch.command_prefix,
                    '--prefix=' + self.get_build_dir(arch.arch),
                    '--disable-builddir',
                    '--enable-shared', _env=env)
            shprint(sh.make, '-j', str(cpu_count()), 'libffi.la', _env=env)

    def get_include_dirs(self, arch):
        return [join(self.get_build_dir(arch.arch), 'include')]


recipe = LibffiRecipe()
