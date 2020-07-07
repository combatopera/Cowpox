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

from cowpox import LibRepo
from cowpox.boot import Bootstrap
from cowpox.config import Config
from cowpox.recipe import BootstrapNDKRecipe
from cowpox.util import Contrib
from diapyr import types
from pathlib import Path

class LibSDL2Recipe(BootstrapNDKRecipe, LibRepo):

    version = "2.0.9"
    url = f"https://www.libsdl.org/release/SDL2-{version}.tar.gz"
    md5sum = 'f2ecfba915c54f7200f504d8b48a5dfe'
    dir_name = 'SDL'
    depends = ['sdl2_image', 'sdl2_mixer', 'sdl2_ttf']

    @types(Config, Bootstrap)
    def __init(self, config, bootstrap):
        self.jnicontrib = Contrib(Path(config.bootstrap.dir, 'jni'), Path(config.bootstrap.common.dir, 'jni'))

    def mainbuild(self):
        self.jnicontrib.mergeinto(self.jni_dir)
        env = self.recipe_env_with_python()
        env['APP_ALLOW_MISSING_DEPS'] = 'true'
        self.ndk_build(env)
        self.builtlibpaths = sorted((self.jni_dir.parent / 'libs' / self.arch.name).iterdir())
