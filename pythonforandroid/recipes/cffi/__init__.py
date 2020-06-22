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
from pythonforandroid.recipe import CompiledComponentsPythonRecipe


class CffiRecipe(CompiledComponentsPythonRecipe):
    """
    Extra system dependencies: autoconf, automake and libtool.
    """
    name = 'cffi'
    version = '1.11.5'
    url = 'https://pypi.python.org/packages/source/c/cffi/cffi-{version}.tar.gz'

    depends = ['setuptools', 'pycparser', 'libffi']

    patches = ['disable-pkg-config.patch']

    # call_hostpython_via_targetpython = False
    install_in_hostpython = True

    def get_hostrecipe_env(self, arch=None):
        # fixes missing ffi.h on some host systems (e.g. gentoo)
        env = super(CffiRecipe, self).get_hostrecipe_env(arch)
        libffi = self.get_recipe('libffi', self.ctx)
        includes = libffi.get_include_dirs(arch)
        env['FFI_INC'] = ",".join(includes)
        return env

    def get_recipe_env(self, arch=None):
        env = super(CffiRecipe, self).get_recipe_env(arch)
        libffi = self.get_recipe('libffi', self.ctx)
        includes = libffi.get_include_dirs(arch)
        env['CFLAGS'] = ' -I'.join([env.get('CFLAGS', '')] + includes)
        env['CFLAGS'] += ' -I{}'.format(self.ctx.python_recipe.include_root(arch.arch))
        env['LDFLAGS'] = (env.get('CFLAGS', '') + ' -L' +
                          self.ctx.get_libs_dir(arch.arch))
        env['LDFLAGS'] += ' -L{}'.format(os.path.join(self.ctx.bootstrap.build_dir, 'libs', arch.arch))
        # required for libc and libdl
        ndk_dir = self.ctx.ndk_platform
        ndk_lib_dir = os.path.join(ndk_dir, 'usr', 'lib')
        env['LDFLAGS'] += ' -L{}'.format(ndk_lib_dir)
        env['PYTHONPATH'] = ':'.join([
            self.ctx.get_site_packages_dir(),
            env['BUILDLIB_PATH'],
        ])
        env['LDFLAGS'] += ' -L{}'.format(self.ctx.python_recipe.link_root(arch.arch))
        env['LDFLAGS'] += ' -lpython{}'.format(self.ctx.python_recipe.major_minor_version_string)
        if 'python3' in self.ctx.python_recipe.name:
            env['LDFLAGS'] += 'm'
        return env


recipe = CffiRecipe()
