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

from pythonforandroid.recipe import CompiledComponentsPythonRecipe, Recipe
from pythonforandroid.toolchain import (
    current_directory,
    info,
    shprint,
)
import sh


class PyCryptoRecipe(CompiledComponentsPythonRecipe):
    version = '2.7a1'
    url = 'https://github.com/dlitz/pycrypto/archive/v{version}.zip'
    depends = ['openssl', ('python2', 'python3')]
    site_packages_name = 'Crypto'
    call_hostpython_via_targetpython = False
    patches = ['add_length.patch']

    def get_recipe_env(self, arch=None):
        env = super(PyCryptoRecipe, self).get_recipe_env(arch)
        openssl_recipe = Recipe.get_recipe('openssl', self.ctx)
        env['CC'] = env['CC'] + openssl_recipe.include_flags(arch)

        env['LDFLAGS'] += ' -L{}'.format(self.ctx.get_libs_dir(arch.arch))
        env['LDFLAGS'] += ' -L{}'.format(self.ctx.libs_dir)
        env['LDFLAGS'] += openssl_recipe.link_dirs_flags(arch)
        env['LIBS'] = env.get('LIBS', '') + openssl_recipe.link_libs_flags()

        env['EXTRA_CFLAGS'] = '--host linux-armv'
        env['ac_cv_func_malloc_0_nonnull'] = 'yes'
        return env

    def build_compiled_components(self, arch):
        info('Configuring compiled components in {}'.format(self.name))

        env = self.get_recipe_env(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            configure = sh.Command('./configure')
            shprint(configure, '--host=arm-eabi',
                    '--prefix={}'.format(self.ctx.get_python_install_dir()),
                    '--enable-shared', _env=env)
        super(PyCryptoRecipe, self).build_compiled_components(arch)


recipe = PyCryptoRecipe()
