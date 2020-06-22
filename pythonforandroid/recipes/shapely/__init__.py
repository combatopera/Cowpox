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

from pythonforandroid.recipe import CythonRecipe
from os.path import join


class ShapelyRecipe(CythonRecipe):
    version = '1.7a1'
    url = 'https://github.com/Toblerity/Shapely/archive/{version}.tar.gz'
    depends = ['setuptools', 'libgeos']

    # Actually, this recipe seems to compile/install fine for python2, but it
    # fails at runtime when importing module with:
    #     `[Errno 2] No such file or directory`
    conflicts = ['python2']

    call_hostpython_via_targetpython = False

    # Patch to avoid libgeos check (because it fails), insert environment
    # variables for our libgeos build (includes, lib paths...) and force
    # the cython's compilation to raise an error in case that it fails
    patches = ['setup.patch']

    # Don't Force Cython
    # setup_extra_args = ['sdist']

    def get_recipe_env(self, arch=None, with_flags_in_cc=True):
        env = super(ShapelyRecipe, self).get_recipe_env(arch)

        libgeos_install = join(self.get_recipe(
            'libgeos', self.ctx).get_build_dir(arch.arch), 'install_target')
        # All this `GEOS_X` variables should be string types, separated
        # by commas in case that we need to pass more than one value
        env['GEOS_INCLUDE_DIRS'] = join(libgeos_install, 'include')
        env['GEOS_LIBRARY_DIRS'] = join(libgeos_install, 'lib')
        env['GEOS_LIBRARIES'] = 'geos_c,geos'

        return env


recipe = ShapelyRecipe()
