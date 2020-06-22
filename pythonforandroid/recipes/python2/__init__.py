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

from os.path import join, exists
from pythonforandroid.recipe import Recipe
from pythonforandroid.python import GuestPythonRecipe
from pythonforandroid.logger import shprint, warning
import sh


class Python2Recipe(GuestPythonRecipe):
    '''
    The python2's recipe.

    .. note:: This recipe can be built only against API 21+

    .. versionchanged:: 0.6.0
        Updated to version 2.7.15 and the build process has been changed in
        favour of the recently added class
        :class:`~pythonforandroid.python.GuestPythonRecipe`
    '''
    version = "2.7.15"
    url = 'https://www.python.org/ftp/python/{version}/Python-{version}.tgz'
    name = 'python2'

    depends = ['hostpython2', 'libffi']
    conflicts = ['python3']

    patches = [
               # new 2.7.15 patches
               # ('patches/fix-api-minor-than-21.patch',
               #  is_api_lt(21)), # Todo: this should be tested
               'patches/fix-missing-extensions.patch',
               'patches/fix-filesystem-default-encoding.patch',
               'patches/fix-gethostbyaddr.patch',
               'patches/fix-posix-declarations.patch',
               'patches/fix-pwd-gecos.patch',
               'patches/fix-ctypes-util-find-library.patch',
               'patches/fix-interpreter-version.patch',
               'patches/fix-zlib-version.patch',
    ]

    configure_args = ('--host={android_host}',
                      '--build={android_build}',
                      '--enable-shared',
                      '--disable-ipv6',
                      '--disable-toolbox-glue',
                      '--disable-framework',
                      'ac_cv_file__dev_ptmx=yes',
                      'ac_cv_file__dev_ptc=no',
                      '--without-ensurepip',
                      'ac_cv_little_endian_double=yes',
                      'ac_cv_header_langinfo_h=no',
                      '--prefix={prefix}',
                      '--exec-prefix={exec_prefix}')

    compiled_extension = '.pyo'

    def prebuild_arch(self, arch):
        super(Python2Recipe, self).prebuild_arch(arch)
        patch_mark = join(self.get_build_dir(arch.arch), '.openssl-patched')
        if 'openssl' in self.ctx.recipe_build_order and not exists(patch_mark):
            self.apply_patch(join('patches', 'enable-openssl.patch'), arch.arch)
            shprint(sh.touch, patch_mark)

    def build_arch(self, arch):
        warning('DEPRECATION: Support for the Python 2 recipe will be '
                'removed in 2020, please upgrade to Python 3.')
        super().build_arch(arch)

    def set_libs_flags(self, env, arch):
        env = super(Python2Recipe, self).set_libs_flags(env, arch)
        if 'libffi' in self.ctx.recipe_build_order:
            # For python2 we need to tell configure that we want to use our
            # compiled libffi, this step is not necessary for python3.
            self.configure_args += ('--with-system-ffi',)

        if 'openssl' in self.ctx.recipe_build_order:
            recipe = Recipe.get_recipe('openssl', self.ctx)
            openssl_build = recipe.get_build_dir(arch.arch)
            env['OPENSSL_BUILD'] = openssl_build
            env['OPENSSL_VERSION'] = recipe.version
        return env


recipe = Python2Recipe()
