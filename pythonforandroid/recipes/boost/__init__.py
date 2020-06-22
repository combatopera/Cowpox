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

from pythonforandroid.util import current_directory, build_platform
from pythonforandroid.recipe import Recipe
from pythonforandroid.logger import shprint
from os.path import join, exists
from os import environ
import shutil
import sh

"""
This recipe bootstraps Boost from source to build Boost.Build
including python bindings
"""


class BoostRecipe(Recipe):
    # Todo: make recipe compatible with all p4a architectures
    '''
    .. note:: This recipe can be built only against API 21+ and an android
              ndk >= r19

    .. versionchanged:: 0.6.0
         Rewrote recipe to support clang's build. The following changes has
         been made:

            - Bumped version number to 1.68.0
            - Better version handling for url
            - Added python 3 compatibility
            - Default compiler for ndk's toolchain set to clang
            - Python version will be detected via user-config.jam
            - Changed stl's lib from ``gnustl_shared`` to ``c++_shared``

    .. versionchanged:: 2019.08.09.1.dev0

            - Bumped version number to 1.68.0
            - Adapted to work with ndk-r19+
    '''
    version = '1.69.0'
    url = (
        'http://downloads.sourceforge.net/project/boost/'
        'boost/{version}/boost_{version_underscore}.tar.bz2'
    )
    depends = [('python2', 'python3')]
    patches = [
        'disable-so-version.patch',
        'use-android-libs.patch',
        'fix-android-issues.patch',
    ]
    need_stl_shared = True

    @property
    def versioned_url(self):
        if self.url is None:
            return None
        return self.url.format(
            version=self.version,
            version_underscore=self.version.replace('.', '_'),
        )

    def should_build(self, arch):
        return not exists(join(self.get_build_dir(arch.arch), 'b2'))

    def prebuild_arch(self, arch):
        super(BoostRecipe, self).prebuild_arch(arch)
        env = self.get_recipe_env(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            # Set custom configuration
            shutil.copyfile(
                join(self.get_recipe_dir(), 'user-config.jam'),
                join(env['BOOST_BUILD_PATH'], 'user-config.jam'),
            )

    def build_arch(self, arch):
        super(BoostRecipe, self).build_arch(arch)
        env = self.get_recipe_env(arch)
        env['PYTHON_HOST'] = self.ctx.hostpython
        with current_directory(self.get_build_dir(arch.arch)):
            if not exists('b2'):
                # Compile Boost.Build engine with this custom toolchain
                bash = sh.Command('bash')
                shprint(bash, 'bootstrap.sh')  # Do not pass env

    def get_recipe_env(self, arch):
        # We don't use the normal env because we
        # are building with a standalone toolchain
        env = environ.copy()

        # find user-config.jam
        env['BOOST_BUILD_PATH'] = self.get_build_dir(arch.arch)
        # find boost source
        env['BOOST_ROOT'] = env['BOOST_BUILD_PATH']

        env['PYTHON_ROOT'] = self.ctx.python_recipe.link_root(arch.arch)
        env['PYTHON_INCLUDE'] = self.ctx.python_recipe.include_root(arch.arch)
        env['PYTHON_MAJOR_MINOR'] = self.ctx.python_recipe.version[:3]
        env[
            'PYTHON_LINK_VERSION'
        ] = self.ctx.python_recipe.major_minor_version_string
        if 'python3' in self.ctx.python_recipe.name:
            env['PYTHON_LINK_VERSION'] += 'm'

        env['ARCH'] = arch.arch.replace('-', '')
        env['TARGET_TRIPLET'] = arch.target
        env['CROSSHOST'] = arch.command_prefix
        env['CROSSHOME'] = join(
            self.ctx.ndk_dir,
            'toolchains/llvm/prebuilt/{build_platform}'.format(
                build_platform=build_platform
            ),
        )
        return env


recipe = BoostRecipe()
