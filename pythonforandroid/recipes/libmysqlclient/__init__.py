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

from pythonforandroid.logger import shprint
from pythonforandroid.recipe import Recipe
from pythonforandroid.util import current_directory
import sh
from os.path import join


class LibmysqlclientRecipe(Recipe):
    name = 'libmysqlclient'
    version = 'master'
    url = 'https://github.com/0x-ff/libmysql-android/archive/{version}.zip'
    # version = '5.5.47'
    # url = 'http://dev.mysql.com/get/Downloads/MySQL-5.5/mysql-{version}.tar.gz'
    #
    # depends = ['ncurses']
    #

    # patches = ['add-custom-platform.patch']

    patches = ['disable-soversion.patch']

    def should_build(self, arch):
        return not self.has_libs(arch, 'libmysql.so')

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        with current_directory(join(self.get_build_dir(arch.arch), 'libmysqlclient')):
            shprint(sh.cp, '-t', '.', join(self.get_recipe_dir(), 'p4a.cmake'))
            # shprint(sh.mkdir, 'Platform')
            # shprint(sh.cp, '-t', 'Platform', join(self.get_recipe_dir(), 'Linux.cmake'))
            shprint(sh.rm, '-f', 'CMakeCache.txt')
            shprint(sh.cmake, '-G', 'Unix Makefiles',
                    # '-DCMAKE_MODULE_PATH=' + join(self.get_build_dir(arch.arch), 'libmysqlclient'),
                    '-DCMAKE_INSTALL_PREFIX=./install',
                    '-DCMAKE_TOOLCHAIN_FILE=p4a.cmake', _env=env)
            shprint(sh.make, _env=env)

            self.install_libs(arch, join('libmysql', 'libmysql.so'))

    # def get_recipe_env(self, arch=None):
    #   env = super(LibmysqlclientRecipe, self).get_recipe_env(arch)
    #   env['WITHOUT_SERVER'] = 'ON'
    #   ncurses = self.get_recipe('ncurses', self)
    #   # env['CFLAGS'] += ' -I' + join(ncurses.get_build_dir(arch.arch),
    #   #                               'include')
    #   env['CURSES_LIBRARY'] = join(self.ctx.get_libs_dir(arch.arch), 'libncurses.so')
    #   env['CURSES_INCLUDE_PATH'] = join(ncurses.get_build_dir(arch.arch),
    #                                     'include')
    #   return env
    #
    # def build_arch(self, arch):
    #   env = self.get_recipe_env(arch)
    #   with current_directory(self.get_build_dir(arch.arch)):
    #       # configure = sh.Command('./configure')
    #       # todo: should add openssl as an optional dep and compile support
    #       # shprint(configure, '--enable-shared', '--enable-assembler',
    #       #         '--enable-thread-safe-client', '--with-innodb',
    #       #         '--without-server', _env=env)
    #       # shprint(sh.make, _env=env)
    #       shprint(sh.cmake, '.', '-DCURSES_LIBRARY=' + env['CURSES_LIBRARY'],
    #               '-DCURSES_INCLUDE_PATH=' + env['CURSES_INCLUDE_PATH'], _env=env)
    #       shprint(sh.make, _env=env)
    #
    #       self.install_libs(arch, 'libmysqlclient.so')


recipe = LibmysqlclientRecipe()
