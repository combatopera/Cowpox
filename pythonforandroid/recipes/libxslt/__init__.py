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

from pythonforandroid.recipe import Recipe
from pythonforandroid.util import current_directory
from pythonforandroid.logger import shprint
from os.path import exists, join
import sh


class LibxsltRecipe(Recipe):
    version = '1.1.32'
    url = 'http://xmlsoft.org/sources/libxslt-{version}.tar.gz'
    depends = ['libxml2']
    patches = ['fix-dlopen.patch']
    built_libraries = {
        'libxslt.a': 'libxslt/.libs',
        'libexslt.a': 'libexslt/.libs'
    }

    call_hostpython_via_targetpython = False

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        build_dir = self.get_build_dir(arch.arch)
        with current_directory(build_dir):
            # If the build is done with /bin/sh things blow up,
            # try really hard to use bash
            libxml2_recipe = Recipe.get_recipe('libxml2', self.ctx)
            libxml2_build_dir = libxml2_recipe.get_build_dir(arch.arch)
            build_arch = shprint(sh.gcc, '-dumpmachine').stdout.decode(
                'utf-8').split('\n')[0]

            if not exists('configure'):
                shprint(sh.Command('./autogen.sh'), _env=env)
            shprint(sh.Command('autoreconf'), '-vif', _env=env)
            shprint(sh.Command('./configure'),
                    '--build=' + build_arch,
                    '--host=' + arch.command_prefix,
                    '--target=' + arch.command_prefix,
                    '--without-plugins',
                    '--without-debug',
                    '--without-python',
                    '--without-crypto',
                    '--with-libxml-src=' + libxml2_build_dir,
                    '--disable-shared',
                    _env=env)
            shprint(sh.make, "V=1", _env=env)

    def get_recipe_env(self, arch):
        env = super(LibxsltRecipe, self).get_recipe_env(arch)
        env['CONFIG_SHELL'] = '/bin/bash'
        env['SHELL'] = '/bin/bash'

        libxml2_recipe = Recipe.get_recipe('libxml2', self.ctx)
        libxml2_build_dir = libxml2_recipe.get_build_dir(arch.arch)
        libxml2_libs_dir = join(libxml2_build_dir, '.libs')

        env['CFLAGS'] = ' '.join([
            env['CFLAGS'],
            '-I' + libxml2_build_dir,
            '-I' + join(libxml2_build_dir, 'include', 'libxml'),
            '-I' + self.get_build_dir(arch.arch),
        ])
        env['LDFLAGS'] += ' -L' + libxml2_libs_dir
        env['LIBS'] = '-lxml2 -lz -lm'

        return env


recipe = LibxsltRecipe()
