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
from os.path import join


class AudiostreamRecipe(CythonRecipe):
    version = 'master'
    url = 'https://github.com/kivy/audiostream/archive/{version}.zip'
    name = 'audiostream'
    depends = [('python2', 'python3'), 'sdl2', 'pyjnius']

    def get_recipe_env(self, arch):
        env = super(AudiostreamRecipe, self).get_recipe_env(arch)
        sdl_include = 'SDL2'
        sdl_mixer_include = 'SDL2_mixer'
        env['USE_SDL2'] = 'True'
        env['SDL2_INCLUDE_DIR'] = join(self.ctx.bootstrap.build_dir, 'jni', 'SDL', 'include')

        env['CFLAGS'] += ' -I{jni_path}/{sdl_include}/include -I{jni_path}/{sdl_mixer_include}'.format(
                              jni_path=join(self.ctx.bootstrap.build_dir, 'jni'),
                              sdl_include=sdl_include,
                              sdl_mixer_include=sdl_mixer_include)
        env['NDKPLATFORM'] = self.ctx.ndk_platform
        env['LIBLINK'] = 'NOTNONE'  # Hacky fix. Needed by audiostream setup.py
        return env


recipe = AudiostreamRecipe()
