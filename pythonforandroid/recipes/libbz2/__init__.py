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

from pythonforandroid.archs import Arch
from pythonforandroid.logger import shprint
from pythonforandroid.recipe import Recipe
from pythonforandroid.util import current_directory


class LibBz2Recipe(Recipe):

    version = "1.0.8"
    url = "https://sourceware.org/pub/bzip2/bzip2-{version}.tar.gz"
    built_libraries = {"libbz2.so": ""}
    patches = ["lib_android.patch"]

    def build_arch(self, arch: Arch) -> None:
        env = self.get_recipe_env(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            shprint(
                sh.make,
                "-j",
                str(cpu_count()),
                f'CC={env["CC"]}',
                f'AR={env["AR"]}',
                f'RANLIB={env["RANLIB"]}',
                "-f",
                "Makefile-libbz2_so",
                _env=env,
            )

    def get_library_includes(self, arch: Arch) -> str:
        """
        Returns a string with the appropriate `-I<lib directory>` to link
        with the bz2 lib. This string is usually added to the environment
        variable `CPPFLAGS`.
        """
        return " -I" + self.get_build_dir(arch.arch)

    def get_library_ldflags(self, arch: Arch) -> str:
        """
        Returns a string with the appropriate `-L<lib directory>` to link
        with the bz2 lib. This string is usually added to the environment
        variable `LDFLAGS`.
        """
        return " -L" + self.get_build_dir(arch.arch)

    @staticmethod
    def get_library_libs_flag() -> str:
        """
        Returns a string with the appropriate `-l<lib>` flags to link with
        the bz2 lib. This string is usually added to the environment
        variable `LIBS`.
        """
        return " -lbz2"


recipe = LibBz2Recipe()
