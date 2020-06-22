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
from pythonforandroid.logger import shprint
from pythonforandroid.util import current_directory
from os.path import join
import sh


class JpegRecipe(Recipe):
    '''
    .. versionchanged:: 0.6.0
        rewrote recipe to be build with clang and updated libraries to latest
        version of the official git repo.
    '''
    name = 'jpeg'
    version = '2.0.1'
    url = 'https://github.com/libjpeg-turbo/libjpeg-turbo/archive/{version}.tar.gz'  # noqa
    built_libraries = {'libjpeg.a': '.', 'libturbojpeg.a': '.'}
    # we will require this below patch to build the shared library
    # patches = ['remove-version.patch']

    def build_arch(self, arch):
        build_dir = self.get_build_dir(arch.arch)

        # TODO: Fix simd/neon
        with current_directory(build_dir):
            env = self.get_recipe_env(arch)
            toolchain_file = join(self.ctx.ndk_dir,
                                  'build/cmake/android.toolchain.cmake')

            shprint(sh.rm, '-f', 'CMakeCache.txt', 'CMakeFiles/')
            shprint(sh.cmake, '-G', 'Unix Makefiles',
                    '-DCMAKE_SYSTEM_NAME=Android',
                    '-DCMAKE_SYSTEM_PROCESSOR={cpu}'.format(cpu='arm'),
                    '-DCMAKE_POSITION_INDEPENDENT_CODE=1',
                    '-DCMAKE_ANDROID_ARCH_ABI={arch}'.format(arch=arch.arch),
                    '-DCMAKE_ANDROID_NDK=' + self.ctx.ndk_dir,
                    '-DCMAKE_C_COMPILER={cc}'.format(cc=arch.get_clang_exe()),
                    '-DCMAKE_CXX_COMPILER={cc_plus}'.format(
                        cc_plus=arch.get_clang_exe(plus_plus=True)),
                    '-DCMAKE_BUILD_TYPE=Release',
                    '-DCMAKE_INSTALL_PREFIX=./install',
                    '-DCMAKE_TOOLCHAIN_FILE=' + toolchain_file,

                    '-DANDROID_ABI={arch}'.format(arch=arch.arch),
                    '-DANDROID_ARM_NEON=ON',
                    '-DENABLE_NEON=ON',
                    # '-DREQUIRE_SIMD=1',

                    # Force disable shared, with the static ones is enough
                    '-DENABLE_SHARED=0',
                    '-DENABLE_STATIC=1',
                    _env=env)
            shprint(sh.make, _env=env)


recipe = JpegRecipe()
