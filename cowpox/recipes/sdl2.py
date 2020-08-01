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

from aridity.config import Config
from cowpox import InterpreterRecipe, LibRepo, ObjRepo
from cowpox.recipe import BootstrapNDKRecipe, Recipe
from cowpox.util import Contrib
from diapyr import types
from itertools import chain
from pathlib import Path
import shutil

class LibSDL2Module(Recipe):

    def installmodule(self, jni_dir):
        # XXX: Would a symlink be sufficient?
        shutil.copytree(self.recipebuilddir, jni_dir / self.dir_name)

class LibSDL2Core(LibSDL2Module):

    name = 'sdl2_core'
    version = '2.0.9'
    dir_name = 'SDL'

    def mainbuild(self):
        self.preparedir(f"https://www.libsdl.org/release/SDL2-{self.version}.tar.gz", 'f2ecfba915c54f7200f504d8b48a5dfe')

class LibSDL2Image(LibSDL2Module):

    name = 'sdl2_image'
    version = '2.0.4'
    dir_name = 'SDL2_image'

    def mainbuild(self):
        self.preparedir(f"https://www.libsdl.org/projects/SDL_image/release/SDL2_image-{self.version}.tar.gz")
        self.apply_patches('toggle_jpg_png_webp.patch', 'extra_cflags.patch')

class LibSDL2Mixer(LibSDL2Module):

    name = 'sdl2_mixer'
    version = '2.0.4'
    dir_name = 'SDL2_mixer'

    def mainbuild(self):
        self.preparedir(f"https://www.libsdl.org/projects/SDL_mixer/release/SDL2_mixer-{self.version}.tar.gz")
        self.apply_patches('toggle_modplug_mikmod_smpeg_ogg.patch')

class LibSDL2TTF(LibSDL2Module):

    name = 'sdl2_ttf'
    version = '2.0.14'
    dir_name = 'SDL2_ttf'

    def mainbuild(self):
        self.preparedir(f"https://www.libsdl.org/projects/SDL_ttf/release/SDL2_ttf-{self.version}.tar.gz")

class LibSDL2Recipe(BootstrapNDKRecipe, LibRepo, ObjRepo):

    name = 'sdl2'
    depends = 'sdl2_core', 'sdl2_image', 'sdl2_mixer', 'sdl2_ttf', 'python3'

    @types(Config, [LibSDL2Module], InterpreterRecipe)
    def __init(self, config, modules, interpreter):
        self.jnicontrib = Contrib([Path(d, 'jni') for d in chain(config.bootstrap.dirs, config.bootstrap.common.dirs)])
        self.modules = modules
        self.interpreter = interpreter

    def mainbuild(self):
        for module in self.modules:
            module.installmodule(self.jni_dir)
        self.jnicontrib.mergeinto(self.jni_dir)
        env = self.interpreter.recipe_env_with_python()
        env['APP_ALLOW_MISSING_DEPS'] = 'true'
        self.ndk_build(env)

    def builtlibpaths(self):
        return sorted((self.recipebuilddir / 'libs' / self.arch.name).iterdir())
