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

import sh

from multiprocessing import cpu_count
from os.path import exists, join

from pythonforandroid.archs import Arch
from pythonforandroid.logger import shprint
from pythonforandroid.recipe import Recipe
from pythonforandroid.util import current_directory, ensure_dir


class LibLzmaRecipe(Recipe):

    version = '5.2.4'
    url = 'https://tukaani.org/xz/xz-{version}.tar.gz'
    built_libraries = {'liblzma.so': 'install/lib'}

    def build_arch(self, arch: Arch) -> None:
        env = self.get_recipe_env(arch)
        install_dir = join(self.get_build_dir(arch.arch), 'install')
        with current_directory(self.get_build_dir(arch.arch)):
            if not exists('configure'):
                shprint(sh.Command('./autogen.sh'), _env=env)
            shprint(sh.Command('autoreconf'), '-vif', _env=env)
            shprint(sh.Command('./configure'),
                    '--host=' + arch.command_prefix,
                    '--prefix=' + install_dir,
                    '--disable-builddir',
                    '--disable-static',
                    '--enable-shared',

                    '--disable-xz',
                    '--disable-xzdec',
                    '--disable-lzmadec',
                    '--disable-lzmainfo',
                    '--disable-scripts',
                    '--disable-doc',

                    _env=env)
            shprint(
                sh.make, '-j', str(cpu_count()),
                _env=env
            )

            ensure_dir('install')
            shprint(sh.make, 'install', _env=env)

    def get_library_includes(self, arch: Arch) -> str:
        """
        Returns a string with the appropriate `-I<lib directory>` to link
        with the lzma lib. This string is usually added to the environment
        variable `CPPFLAGS`.
        """
        return " -I" + join(
            self.get_build_dir(arch.arch), 'install', 'include',
        )

    def get_library_ldflags(self, arch: Arch) -> str:
        """
        Returns a string with the appropriate `-L<lib directory>` to link
        with the lzma lib. This string is usually added to the environment
        variable `LDFLAGS`.
        """
        return " -L" + join(
            self.get_build_dir(arch.arch), self.built_libraries['liblzma.so'],
        )

    @staticmethod
    def get_library_libs_flag() -> str:
        """
        Returns a string with the appropriate `-l<lib>` flags to link with
        the lzma lib. This string is usually added to the environment
        variable `LIBS`.
        """
        return " -llzma"


recipe = LibLzmaRecipe()
