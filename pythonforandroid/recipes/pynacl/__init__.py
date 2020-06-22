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
import os


class PyNaCLRecipe(CompiledComponentsPythonRecipe):
    name = 'pynacl'
    version = '1.3.0'
    url = 'https://pypi.python.org/packages/source/P/PyNaCl/PyNaCl-{version}.tar.gz'

    depends = [('hostpython2', 'hostpython3'), 'six', 'setuptools', 'cffi', 'libsodium']
    call_hostpython_via_targetpython = False

    def get_recipe_env(self, arch):
        env = super(PyNaCLRecipe, self).get_recipe_env(arch)
        env['SODIUM_INSTALL'] = 'system'

        libsodium_build_dir = self.get_recipe(
            'libsodium', self.ctx).get_build_dir(arch.arch)
        env['CFLAGS'] += ' -I{}'.format(os.path.join(libsodium_build_dir,
                                                     'src/libsodium/include'))
        env['LDFLAGS'] += ' -L{}'.format(
            self.ctx.get_libs_dir(arch.arch) +
            '-L{}'.format(self.ctx.libs_dir)) + ' -L{}'.format(
            libsodium_build_dir)

        return env


recipe = PyNaCLRecipe()
