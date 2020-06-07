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

from p4a import CythonRecipe
from p4a.patch import will_build
from types import MappingProxyType
import logging

log = logging.getLogger(__name__)

class AndroidRecipe(CythonRecipe):

    version = None # XXX: Needed?
    url = 'src'
    depends = [('sdl2', 'genericndkbuild'), 'pyjnius']
    config_env = MappingProxyType({}) # XXX: Needed?

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        env.update(self.config_env)
        return env

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        bootstrap_name = self.ctx.bootstrap.name
        is_sdl2 = bootstrap_name in {'sdl2', 'sdl2python3', 'sdl2_gradle'}
        is_webview = bootstrap_name == 'webview'
        is_service_only = bootstrap_name == 'service_only'
        if not (is_sdl2 or is_webview or is_service_only):
            raise Exception("unsupported bootstrap for android recipe: %s" % bootstrap_name)
        config = {
            'BOOTSTRAP': 'sdl2' if is_sdl2 else bootstrap_name,
            'IS_SDL2': int(is_sdl2),
            'PY2': int(will_build('python2')(self)),
            'JAVA_NAMESPACE': 'org.kivy.android',
            'JNI_NAMESPACE': 'org/kivy/android',
        }
        android = self.get_build_dir(arch) / 'android'
        with (android / 'config.pxi').open('w') as fpxi, (android / 'config.h').open('w') as fh, (android / 'config.py').open('w') as fpy:
            for key, value in config.items():
                print(f'DEF {key} = {repr(value)}', file = fpxi)
                print(f'{key} = {repr(value)}', file = fpy)
                print(f"""#define {key} {value if isinstance(value, int) else f'"{value}"'}""", file = fh)
            if is_sdl2:
                print('JNIEnv *SDL_AndroidGetJNIEnv(void);', file = fh)
                print('#define SDL_ANDROID_GetJNIEnv SDL_AndroidGetJNIEnv', file = fh)
        self.config_env = {key: str(value) for key, value in config.items()}
