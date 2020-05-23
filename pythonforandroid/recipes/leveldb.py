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
from pythonforandroid.util import current_directory
from pythonforandroid.recipe import Recipe
from multiprocessing import cpu_count
from os.path import join
import sh


class LevelDBRecipe(Recipe):
    version = '1.22'
    url = 'https://github.com/google/leveldb/archive/{version}.tar.gz'
    depends = ['snappy']
    built_libraries = {'libleveldb.so': '.'}
    need_stl_shared = True

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        source_dir = self.get_build_dir(arch.arch)
        with current_directory(source_dir):
            snappy_recipe = self.get_recipe('snappy', self.ctx)
            snappy_build = snappy_recipe.get_build_dir(arch.arch)

            shprint(sh.cmake, source_dir,
                    '-DANDROID_ABI={}'.format(arch.arch),
                    '-DANDROID_NATIVE_API_LEVEL={}'.format(self.ctx.ndk_api),
                    '-DANDROID_STL=' + self.stl_lib_name,

                    '-DCMAKE_TOOLCHAIN_FILE={}'.format(
                        join(self.ctx.ndk_dir, 'build', 'cmake',
                             'android.toolchain.cmake')),
                    '-DCMAKE_BUILD_TYPE=Release',

                    '-DBUILD_SHARED_LIBS=1',

                    '-DHAVE_SNAPPY=1',
                    '-DCMAKE_CXX_FLAGS=-I{path}'.format(path=snappy_build),
                    '-DCMAKE_SHARED_LINKER_FLAGS=-L{path} -lsnappy'.format(
                        path=snappy_build),
                    '-DCMAKE_EXE_LINKER_FLAGS=-L{path} -lsnappy'.format(
                        path=snappy_build),

                    _env=env)
            shprint(sh.make, '-j' + str(cpu_count()), _env=env)


recipe = LevelDBRecipe()
