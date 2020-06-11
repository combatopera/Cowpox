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

from diapyr import types
from lagoon import make, perl
from p4a.recipe import Recipe
from seizure.config import Config

class OpenSSLRecipe(Recipe):

    version = '1.1'
    url_version = '1.1.1f'
    url = f"https://www.openssl.org/source/openssl-{url_version}.tar.gz"
    builtlibpaths = [f"libcrypto{version}.so", f"libssl{version}.so"]

    @types(Config)
    def __init(self, config):
        self.ndk_dir = Path(config.android_ndk_dir)
        self.ndk_api = config.android.ndk_api

    def get_build_dir(self, arch):
        return self.get_build_container_dir(arch) / f"{self.name}{self.version}"

    def include_flags(self, arch):
        openssl_includes = self.get_build_dir(arch) / 'include'
        return f" -I{openssl_includes} -I{openssl_includes / 'internal'} -I{openssl_includes / 'openssl'}"

    def link_dirs_flags(self, arch):
        return f" -L{self.get_build_dir(arch)}"

    def link_libs_flags(self):
        return f" -lcrypto{self.version} -lssl{self.version}"

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        env['OPENSSL_VERSION'] = self.version
        env['MAKE'] = 'make'
        env['ANDROID_NDK'] = str(self.ndk_dir)
        return env

    def _select_build_arch(self, arch):
        aname = arch.name
        if 'arm64' in aname:
            return 'android-arm64'
        if 'v7a' in aname:
            return 'android-arm'
        if 'arm' in aname:
            return 'android'
        if 'x86_64' in aname:
            return 'android-x86_64'
        if 'x86' in aname:
            return 'android-x86'
        return 'linux-armv4'

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        cwd = self.get_build_dir(arch)
        perl.print('Configure', 'shared', 'no-dso', 'no-asm', self._select_build_arch(arch), f"-D__ANDROID_API__={self.ndk_api}", env = env, cwd = cwd)
        self.apply_patch('disable-sover.patch', arch)
        make.print('build_libs', env = env, cwd = cwd)
