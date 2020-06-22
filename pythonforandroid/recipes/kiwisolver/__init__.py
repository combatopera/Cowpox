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

from pythonforandroid.recipe import CppCompiledComponentsPythonRecipe


class KiwiSolverRecipe(CppCompiledComponentsPythonRecipe):
    site_packages_name = 'kiwisolver'
    # Pin to commit `docs: attempt to fix doc building`, the latest one
    # at the time of writing, just to be sure that we have te most up to date
    # version, but it should be pinned to an official release once the c++
    # changes that we want to include are merged to master branch
    #   Note: the commit we want to include is
    #         `Cppy use update and c++11 compatibility` (4858730)
    version = '0846189'
    url = 'https://github.com/nucleic/kiwi/archive/{version}.zip'
    depends = ['cppy']

    def get_recipe_env(self, arch=None, with_flags_in_cc=True):
        env = super().get_recipe_env(arch, with_flags_in_cc)
        if self.need_stl_shared:
            # kiwisolver compile flags does not honor the standard flags:
            # `CPPFLAGS` and `LDLIBS`, so we put in `CFLAGS` and `LDFLAGS` to
            # correctly link with the `c++_shared` library
            env['CFLAGS'] += f' -I{self.stl_include_dir}'
            env['CFLAGS'] += ' -frtti -fexceptions'

            env['LDFLAGS'] += f' -L{self.get_stl_lib_dir(arch)}'
            env['LDFLAGS'] += f' -l{self.stl_lib_name}'
        return env


recipe = KiwiSolverRecipe()
