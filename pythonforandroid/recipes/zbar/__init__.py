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

from os.path import join
from pythonforandroid.recipe import PythonRecipe


class ZBarRecipe(PythonRecipe):

    version = '0.10'

    # For some reason the version 0.10 on PyPI is not the same as the ones
    # in sourceforge and GitHub. The one in PyPI has a setup.py.
    # url = 'https://github.com/ZBar/ZBar/archive/{version}.zip'
    url = 'https://pypi.python.org/packages/e0/5c/' + \
        'bd2a96a9f2adacffceb4482cdd56831735ab5a67ea6a60c0a8757c17b62e' + \
        '/zbar-{version}.tar.gz'

    call_hostpython_via_targetpython = False

    depends = ['setuptools', 'libzbar']

    patches = ["zbar-0.10-python-crash.patch"]

    def get_recipe_env(self, arch=None, with_flags_in_cc=True):
        env = super(ZBarRecipe, self).get_recipe_env(arch, with_flags_in_cc)
        libzbar = self.get_recipe('libzbar', self.ctx)
        libzbar_dir = libzbar.get_build_dir(arch.arch)
        env['PYTHON_ROOT'] = self.ctx.get_python_install_dir()
        env['CFLAGS'] += ' -I' + join(libzbar_dir, 'include')
        env['LDFLAGS'] += ' -L' + join(libzbar_dir, 'zbar', '.libs')
        env['LIBS'] = env.get('LIBS', '') + ' -landroid -lzbar'
        return env


recipe = ZBarRecipe()
