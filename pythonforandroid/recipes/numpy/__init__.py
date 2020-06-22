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

from pythonforandroid.recipe import CompiledComponentsPythonRecipe
from multiprocessing import cpu_count
from os.path import join


class NumpyRecipe(CompiledComponentsPythonRecipe):

    version = '1.18.1'
    url = 'https://pypi.python.org/packages/source/n/numpy/numpy-{version}.zip'
    site_packages_name = 'numpy'
    depends = ['setuptools', 'cython']

    patches = [
        join('patches', 'add_libm_explicitly_to_build.patch'),
        join('patches', 'do_not_use_system_libs.patch'),
        join('patches', 'remove_unittest_call.patch'),
        ]

    call_hostpython_via_targetpython = False

    def apply_patches(self, arch, build_dir=None):
        if 'python2' in self.ctx.recipe_build_order:
            self.patches.append(join('patches', 'fix-py2-numpy-import.patch'))
        super().apply_patches(arch, build_dir=build_dir)

    def build_compiled_components(self, arch):
        self.setup_extra_args = ['-j', str(cpu_count())]
        super().build_compiled_components(arch)
        self.setup_extra_args = []

    def rebuild_compiled_components(self, arch, env):
        self.setup_extra_args = ['-j', str(cpu_count())]
        super().rebuild_compiled_components(arch, env)
        self.setup_extra_args = []


recipe = NumpyRecipe()
