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

import os
from pythonforandroid.recipe import Recipe
from pythonforandroid.util import current_directory
from pythonforandroid.logger import shprint
from multiprocessing import cpu_count
import sh


class LibZBarRecipe(Recipe):

    version = '0.10'

    url = 'https://github.com/ZBar/ZBar/archive/{version}.zip'

    depends = ['libiconv']

    patches = ["werror.patch"]

    built_libraries = {'libzbar.so': 'zbar/.libs'}

    def get_recipe_env(self, arch=None, with_flags_in_cc=True):
        env = super(LibZBarRecipe, self).get_recipe_env(arch, with_flags_in_cc)
        libiconv = self.get_recipe('libiconv', self.ctx)
        libiconv_dir = libiconv.get_build_dir(arch.arch)
        env['CFLAGS'] += ' -I' + os.path.join(libiconv_dir, 'include')
        env['LIBS'] = env.get('LIBS', '') + ' -landroid -liconv'
        return env

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            shprint(sh.Command('autoreconf'), '-vif', _env=env)
            shprint(
                sh.Command('./configure'),
                '--host=' + arch.command_prefix,
                '--target=' + arch.toolchain_prefix,
                '--prefix=' + self.ctx.get_python_install_dir(),
                # Python bindings are compiled in a separated recipe
                '--with-python=no',
                '--with-gtk=no',
                '--with-qt=no',
                '--with-x=no',
                '--with-jpeg=no',
                '--with-imagemagick=no',
                '--enable-pthread=no',
                '--enable-video=no',
                '--enable-shared=yes',
                '--enable-static=no',
                _env=env)
            shprint(sh.make, '-j' + str(cpu_count()), _env=env)


recipe = LibZBarRecipe()
