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

import sh
from pythonforandroid.python import GuestPythonRecipe
from pythonforandroid.recipe import Recipe
from pythonforandroid.patching import version_starts_with


class Python3Recipe(GuestPythonRecipe):
    '''
    The python3's recipe
    ^^^^^^^^^^^^^^^^^^^^

    The python 3 recipe can be built with some extra python modules, but to do
    so, we need some libraries. By default, we ship the python3 recipe with
    some common libraries, defined in ``depends``. We also support some optional
    libraries, which are less common that the ones defined in ``depends``, so
    we added them as optional dependencies (``opt_depends``).

    Below you have a relationship between the python modules and the recipe
    libraries::

        - _ctypes: you must add the recipe for ``libffi``.
        - _sqlite3: you must add the recipe for ``sqlite3``.
        - _ssl: you must add the recipe for ``openssl``.
        - _bz2: you must add the recipe for ``libbz2`` (optional).
        - _lzma: you must add the recipe for ``liblzma`` (optional).

    .. note:: This recipe can be built only against API 21+.

    .. versionchanged:: 2019.10.06.post0
        Added optional dependencies: :mod:`~pythonforandroid.recipes.libbz2`
        and :mod:`~pythonforandroid.recipes.liblzma`
    .. versionchanged:: 0.6.0
        Refactored into class
        :class:`~pythonforandroid.python.GuestPythonRecipe`
    '''

    version = '3.8.1'
    url = 'https://www.python.org/ftp/python/{version}/Python-{version}.tgz'
    name = 'python3'

    patches = [
        # Python 3.7.1
        ('patches/py3.7.1_fix-ctypes-util-find-library.patch', version_starts_with("3.7")),
        ('patches/py3.7.1_fix-zlib-version.patch', version_starts_with("3.7")),

        # Python 3.8.1
        ('patches/py3.8.1.patch', version_starts_with("3.8"))
    ]

    if sh.which('lld') is not None:
        patches = patches + [
            ("patches/py3.7.1_fix_cortex_a8.patch", version_starts_with("3.7")),
            ("patches/py3.8.1_fix_cortex_a8.patch", version_starts_with("3.8"))
        ]

    depends = ['hostpython3', 'sqlite3', 'openssl', 'libffi']
    # those optional depends allow us to build python compression modules:
    #   - _bz2.so
    #   - _lzma.so
    opt_depends = ['libbz2', 'liblzma']
    conflicts = ['python2']
    configure_args = (
        '--host={android_host}',
        '--build={android_build}',
        '--enable-shared',
        '--enable-ipv6',
        'ac_cv_file__dev_ptmx=yes',
        'ac_cv_file__dev_ptc=no',
        '--without-ensurepip',
        'ac_cv_little_endian_double=yes',
        '--prefix={prefix}',
        '--exec-prefix={exec_prefix}',
    )

    def set_libs_flags(self, env, arch):
        env = super().set_libs_flags(env, arch)
        if 'openssl' in self.ctx.recipe_build_order:
            recipe = Recipe.get_recipe('openssl', self.ctx)
            self.configure_args += (f"--with-openssl={recipe.get_build_dir(arch.arch)}",)
        return env

recipe = Python3Recipe()
