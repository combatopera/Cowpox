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

from cowpox.pyrecipe import CythonRecipe
from diapyr import types
import os, shutil

class KivyRecipe(CythonRecipe):

    from .sdl2 import LibSDL2Recipe
    name = 'Kivy'
    version = '1.11.1' # TODO: Upgrade.
    depends = 'sdl2', 'pyjnius', 'setuptools', 'certifi' # XXX: Can we get (some of) these from setup.py?

    @types(LibSDL2Recipe)
    def __init(self, sdl2 = None):
        self.sdl2 = sdl2

    def cythonize_build(self, env):
        super().cythonize_build(env)
        kivyinclude = self.recipebuilddir / 'kivy' / 'include'
        if kivyinclude.exists():
            for dirn in self.recipebuilddir.glob('build/lib.*'):
                shutil.copytree(kivyinclude, dirn / 'kivy' / 'include')

    def pyxpaths(self):
        for path in super().pyxpaths():
            if path.name != 'window_x11.pyx':
                yield path

    def mainbuild(self):
        self.preparedir(f"https://github.com/kivy/kivy/archive/{self.version}.zip")
        env = self.get_recipe_env()
        if self.sdl2 is not None:
            env['USE_SDL2'] = '1'
            env['KIVY_SPLIT_EXAMPLES'] = '1'
            env['KIVY_SDL2_PATH'] = os.pathsep.join(map(str, [
                self.sdl2.jni_dir / 'SDL' / 'include',
                self.sdl2.jni_dir / 'SDL2_image',
                self.sdl2.jni_dir / 'SDL2_mixer',
                self.sdl2.jni_dir / 'SDL2_ttf',
            ]))
        self.install_python_package(env)
