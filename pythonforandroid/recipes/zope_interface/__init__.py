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

from pythonforandroid.recipe import PythonRecipe
from pythonforandroid.toolchain import current_directory
from os.path import join
import sh


class ZopeInterfaceRecipe(PythonRecipe):
    call_hostpython_via_targetpython = False
    name = 'zope_interface'
    version = '4.1.3'
    url = 'https://pypi.python.org/packages/source/z/zope.interface/zope.interface-{version}.tar.gz'
    site_packages_name = 'zope.interface'
    depends = ['setuptools']
    patches = ['no_tests.patch']

    def build_arch(self, arch):
        super(ZopeInterfaceRecipe, self).build_arch(arch)
        # The zope.interface module lacks of the __init__.py file in one of his
        # folders (once is installed), that leads into an ImportError.
        # Here we intentionally apply a patch to solve that, so, in case that
        # this is solved in the future an error will be triggered
        zope_install = join(self.ctx.get_site_packages_dir(arch.arch), 'zope')
        self.apply_patch('fix-init.patch', arch.arch, build_dir=zope_install)

    def prebuild_arch(self, arch):
        super(ZopeInterfaceRecipe, self).prebuild_arch(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            sh.rm(
                '-rf',
                'src/zope/interface/tests',
                'src/zope/interface/common/tests',
            )


recipe = ZopeInterfaceRecipe()
