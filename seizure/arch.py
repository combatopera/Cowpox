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

from .config import Config
from .platform import Platform
from diapyr import types
from diapyr.util import singleton
from lagoon import which
from multiprocessing import cpu_count
import os

def _spjoin(*v):
    return ' '.join(map(str, v))

class Arch:

    build_platform = f"{os.uname()[0]}-{os.uname()[-1]}".lower()
    ccachepath, = which('ccache').splitlines()
    staticenv = dict(
        LDLIBS = '-lm',
        USE_CCACHE = '1',
        NDK_CCACHE = ccachepath,
        MAKE = f"make -j{cpu_count()}",
        **{k: v for k, v in os.environ.items() if k.startswith('CCACHE_')},
    )

    @types(Config, Platform)
    def __init__(self, config, platform):
        self.ndk_api = config.android.ndk_api
        self.cflags = _spjoin(
            '-target',
            self.target(),
            '-fomit-frame-pointer',
            *self.arch_cflags,
        )
        self.cc = _spjoin(self.ccachepath, platform.clang_exe(self), self.cflags)
        self.archenv = dict(self.staticenv,
            CFLAGS = self.cflags,
            CXXFLAGS = self.cflags,
            CC = self.cc,
            CXX = _spjoin(self.ccachepath, platform.clang_exe(self, plus_plus = True), self.cflags),
            AR = f"{self.command_prefix}-ar",
            RANLIB = f"{self.command_prefix}-ranlib",
            STRIP = f"{self.command_prefix}-strip --strip-unneeded",
            READELF = f"{self.command_prefix}-readelf",
            NM = f"{self.command_prefix}-nm",
            LD = f"{self.command_prefix}-ld",
            ARCH = self.name,
            NDK_API = f"android-{self.ndk_api}",
            TOOLCHAIN_PREFIX = self.toolchain_prefix,
            TOOLCHAIN_VERSION = platform.toolchain_version(self),
            LDSHARED = _spjoin(
                self.cc,
                '-pthread',
                '-shared',
                '-Wl,-O1',
                '-Wl,-Bsymbolic-functions',
            ),
            PATH = f"{platform.clang_path(self)}{os.pathsep}{os.environ['PATH']}", # XXX: Is clang_path really needed?
        )
        self.cppflags = _spjoin(
            '-DANDROID',
            f"-D__ANDROID_API__={self.ndk_api}",
            f"-I{platform.includepath(self)}",
        )

    def target(self):
        return f"{self.command_prefix}{self.ndk_api}"

    def builddirname(self):
        return f"{self.name}__ndk_target_{self.ndk_api}"

    def get_env(self, ctx):
        return dict(self.archenv,
            CPPFLAGS = f"""{self.cppflags} -I{ctx.get_python_install_dir() / 'include' / f"python{ctx.python_recipe.version[:3]}"}""",
            LDFLAGS = f"-L{ctx.get_libs_dir(self)}",
            BUILDLIB_PATH = ctx.get_recipe(f"host{ctx.python_recipe.name}").get_build_dir(self) / 'native-build' / 'build' / f"lib.{self.build_platform}-{ctx.python_recipe.major_minor_version_string}",
        )

@singleton
class DesktopArch:

    def builddirname(self):
        return 'desktop'

class BaseArchARM(Arch):

    toolchain_prefix = 'arm-linux-androideabi'
    command_prefix = 'arm-linux-androideabi'
    platform_dir = 'arch-arm'

    def target(self):
        return f"armv7a-linux-androideabi{self.ndk_api}"

class ArchARM(BaseArchARM):

    name = "armeabi"
    arch_cflags = []
    numver = 1

class ArchARMv7_a(BaseArchARM):

    name = 'armeabi-v7a'
    arch_cflags = [
        '-march=armv7-a',
        '-mfloat-abi=softfp',
        '-mfpu=vfp',
        '-mthumb',
        '-fPIC',
    ]
    numver = 7

class Archx86(Arch):

    name = 'x86'
    toolchain_prefix = 'x86'
    command_prefix = 'i686-linux-android'
    platform_dir = 'arch-x86'
    arch_cflags = [
        '-march=i686',
        '-mtune=intel',
        '-mssse3',
        '-mfpmath=sse',
        '-m32',
    ]
    numver = 6

class Archx86_64(Arch):

    name = 'x86_64'
    toolchain_prefix = 'x86_64'
    command_prefix = 'x86_64-linux-android'
    platform_dir = 'arch-x86_64'
    arch_cflags = [
        '-march=x86-64',
        '-msse4.2',
        '-mpopcnt',
        '-m64',
        '-mtune=intel',
        '-fPIC',
    ]
    numver = 9

class ArchAarch_64(Arch):

    name = 'arm64-v8a'
    toolchain_prefix = 'aarch64-linux-android'
    command_prefix = 'aarch64-linux-android'
    platform_dir = 'arch-arm64'
    arch_cflags = [
        '-march=armv8-a',
    ]
    numver = 8

all_archs = {a.name: a for a in [ArchARM, ArchARMv7_a, Archx86, Archx86_64, ArchAarch_64]}
