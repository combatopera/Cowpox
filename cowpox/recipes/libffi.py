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

from cowpox import LibRepo
from cowpox.recipe import Recipe
from lagoon import autoreconf, make
from lagoon.program import Program
from multiprocessing import cpu_count
from pathlib import Path

class LibffiRecipe(Recipe, LibRepo):

    name = 'libffi'
    version = '8fa8837'

    def mainbuild(self):
        self.preparedir(f"https://github.com/libffi/libffi/archive/{self.version}.tar.gz")
        self.apply_patches('remove-version-info.patch')
        env = self.arch.env
        if not (self.recipebuilddir / 'configure').exists():
            Program.text(Path('autogen.sh'))[print](env = env, cwd = self.recipebuilddir)
        autoreconf._vif[print](env = env, cwd = self.recipebuilddir)
        Program.text(Path('configure'))[print](
                f"--host={self.arch.command_prefix}", f"--prefix={self.recipebuilddir}", '--disable-builddir', '--enable-shared', env = env, cwd = self.recipebuilddir)
        make[print]('-j', cpu_count(), 'libffi.la', env = env, cwd = self.recipebuilddir)
        self.striplibs()

    def builtlibpaths(self):
        return [Path('.libs', 'libffi.so')]

    def includeslinkslibs(self):
        return [[self.recipebuilddir / 'include'], [self.recipebuilddir / '.libs'], ['ffi']]
