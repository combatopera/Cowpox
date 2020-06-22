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
from os.path import exists
import sh


class Libxml2Recipe(Recipe):
    version = '2.9.8'
    url = 'http://xmlsoft.org/sources/libxml2-{version}.tar.gz'
    depends = []
    patches = ['add-glob.c.patch']
    built_libraries = {'libxml2.a': '.libs'}

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        with current_directory(self.get_build_dir(arch.arch)):

            if not exists('configure'):
                shprint(sh.Command('./autogen.sh'), _env=env)
            shprint(sh.Command('autoreconf'), '-vif', _env=env)
            build_arch = shprint(
                sh.gcc, '-dumpmachine').stdout.decode('utf-8').split('\n')[0]
            shprint(sh.Command('./configure'),
                    '--build=' + build_arch,
                    '--host=' + arch.command_prefix,
                    '--target=' + arch.command_prefix,
                    '--without-modules',
                    '--without-legacy',
                    '--without-history',
                    '--without-debug',
                    '--without-docbook',
                    '--without-python',
                    '--without-threads',
                    '--without-iconv',
                    '--without-lzma',
                    '--disable-shared',
                    '--enable-static',
                    _env=env)

            # Ensure we only build libxml2.la as if we do everything
            # we'll need the glob dependency which is a big headache
            shprint(sh.make, "libxml2.la", _env=env)

    def get_recipe_env(self, arch):
        env = super(Libxml2Recipe, self).get_recipe_env(arch)
        env['CONFIG_SHELL'] = '/bin/bash'
        env['SHELL'] = '/bin/bash'
        env['CC'] += ' -I' + self.get_build_dir(arch.arch)
        return env


recipe = Libxml2Recipe()
