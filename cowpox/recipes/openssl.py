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
from cowpox import LibRepo
from cowpox.recipe import Recipe
from diapyr import types
from lagoon import make, perl

class OpenSSLRecipe(Recipe, LibRepo):

    name = 'OpenSSL'
    version = '1.1'

    @types(Config)
    def __init(self, config):
        self.ndk_dir = config.NDK.dir
        self.ndk_api = config.android.ndk_api

    def includeslinkslibs(self):
        return (
            [self.recipebuilddir / 'include' / p for p in ['.', 'internal', 'openssl']],
            [self.recipebuilddir],
            [f"crypto{self.version}", f"ssl{self.version}"],
        )

    def _select_build_arch(self):
        aname = self.arch.name
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

    def mainbuild(self):
        self.preparedir('https://www.openssl.org/source/openssl-1.1.1f.tar.gz')
        env = self.arch.env.copy()
        env['OPENSSL_VERSION'] = self.version
        env['MAKE'] = 'make'
        env['ANDROID_NDK'] = self.ndk_dir
        perl[print]('Configure', 'shared', 'no-dso', 'no-asm', self._select_build_arch(), f"-D__ANDROID_API__={self.ndk_api}", env = env, cwd = self.recipebuilddir)
        self.apply_patches('disable-sover.patch')
        make[print]('build_libs', env = env, cwd = self.recipebuilddir)
        self.striplibs()

    def builtlibpaths(self):
        return [f"libcrypto{self.version}.so", f"libssl{self.version}.so"]
