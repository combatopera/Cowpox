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
from pythonforandroid.recipe import PythonRecipe
from pythonforandroid.util import current_directory
import sh

class ApswRecipe(PythonRecipe):

    version = '3.15.0-r1'
    url = 'https://github.com/rogerbinns/apsw/archive/{version}.tar.gz'
    depends = ['sqlite3', ('python2', 'python3'), 'setuptools']
    call_hostpython_via_targetpython = False
    site_packages_name = 'apsw'

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            # Build python bindings
            hostpython = sh.Command(self.hostpython_location)
            shprint(hostpython,
                    'setup.py',
                    'build_ext',
                    '--enable=fts4', _env=env)
        # Install python bindings
        super(ApswRecipe, self).build_arch(arch)

    def get_recipe_env(self, arch):
        env = super(ApswRecipe, self).get_recipe_env(arch)
        sqlite_recipe = self.get_recipe('sqlite3', self.ctx)
        env['CFLAGS'] += ' -I' + sqlite_recipe.get_build_dir(arch.arch)
        env['LDFLAGS'] += ' -L' + sqlite_recipe.get_lib_dir(arch)
        env['LIBS'] = env.get('LIBS', '') + ' -lsqlite3'
        return env

recipe = ApswRecipe()
