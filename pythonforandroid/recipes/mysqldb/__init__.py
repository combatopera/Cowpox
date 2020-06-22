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
from os.path import join


class MysqldbRecipe(CompiledComponentsPythonRecipe):
    name = 'mysqldb'
    version = '1.2.5'
    url = 'https://pypi.python.org/packages/source/M/MySQL-python/MySQL-python-{version}.zip'
    site_packages_name = 'MySQLdb'

    depends = ['setuptools', 'libmysqlclient']

    patches = ['override-mysql-config.patch',
               'disable-zip.patch']

    # call_hostpython_via_targetpython = False

    def convert_newlines(self, filename):
        print('converting newlines in {}'.format(filename))
        with open(filename, 'rb') as f:
            data = f.read()
        with open(filename, 'wb') as f:
            f.write(data.replace(b'\r\n', b'\n').replace(b'\r', b'\n'))

    def prebuild_arch(self, arch):
        super(MysqldbRecipe, self).prebuild_arch(arch)
        setupbase = join(self.get_build_dir(arch.arch), 'setup')
        self.convert_newlines(setupbase + '.py')
        self.convert_newlines(setupbase + '_posix.py')

    def get_recipe_env(self, arch=None):
        env = super(MysqldbRecipe, self).get_recipe_env(arch)

        hostpython = self.get_recipe('hostpython2', self.ctx)
        # TODO: fix hardcoded path
        env['PYTHONPATH'] = (join(hostpython.get_build_dir(arch.arch),
                                  'build', 'lib.linux-x86_64-2.7') +
                             ':' + env.get('PYTHONPATH', ''))

        libmysql = self.get_recipe('libmysqlclient', self.ctx)
        mydir = join(libmysql.get_build_dir(arch.arch), 'libmysqlclient')
        # env['CFLAGS'] += ' -I' + join(mydir, 'include')
        # env['LDFLAGS'] += ' -L' + join(mydir)
        libdir = self.ctx.get_libs_dir(arch.arch)
        env['MYSQL_libs'] = env['MYSQL_libs_r'] = '-L' + libdir + ' -lmysql'
        env['MYSQL_cflags'] = env['MYSQL_include'] = '-I' + join(mydir,
                                                                 'include')

        return env


recipe = MysqldbRecipe()
