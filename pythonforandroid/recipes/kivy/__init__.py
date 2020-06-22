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

from pythonforandroid.recipe import CythonRecipe
from pythonforandroid.toolchain import current_directory, shprint
from os.path import exists, join, basename
import sh
import glob


class KivyRecipe(CythonRecipe):
    version = '1.11.1'
    url = 'https://github.com/kivy/kivy/archive/{version}.zip'
    name = 'kivy'

    depends = ['sdl2', 'pyjnius', 'setuptools']
    python_depends = ['certifi']

    def cythonize_build(self, env, build_dir='.'):
        super(KivyRecipe, self).cythonize_build(env, build_dir=build_dir)

        if not exists(join(build_dir, 'kivy', 'include')):
            return

        # If kivy is new enough to use the include dir, copy it
        # manually to the right location as we bypass this stage of
        # the build
        with current_directory(build_dir):
            build_libs_dirs = glob.glob(join('build', 'lib.*'))

            for dirn in build_libs_dirs:
                shprint(sh.cp, '-r', join('kivy', 'include'),
                        join(dirn, 'kivy'))

    def cythonize_file(self, env, build_dir, filename):
        # We can ignore a few files that aren't important to the
        # android build, and may not work on Android anyway
        do_not_cythonize = ['window_x11.pyx', ]
        if basename(filename) in do_not_cythonize:
            return
        super(KivyRecipe, self).cythonize_file(env, build_dir, filename)

    def get_recipe_env(self, arch):
        env = super(KivyRecipe, self).get_recipe_env(arch)
        if 'sdl2' in self.ctx.recipe_build_order:
            env['USE_SDL2'] = '1'
            env['KIVY_SPLIT_EXAMPLES'] = '1'
            env['KIVY_SDL2_PATH'] = ':'.join([
                join(self.ctx.bootstrap.build_dir, 'jni', 'SDL', 'include'),
                join(self.ctx.bootstrap.build_dir, 'jni', 'SDL2_image'),
                join(self.ctx.bootstrap.build_dir, 'jni', 'SDL2_mixer'),
                join(self.ctx.bootstrap.build_dir, 'jni', 'SDL2_ttf'),
                ])

        return env


recipe = KivyRecipe()
