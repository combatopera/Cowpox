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

from . import Arch
from .platform import Platform
from aridity.config import Config
from diapyr import types
from lagoon.program import partial, Program
from multiprocessing import cpu_count
import logging, os, shutil

log = logging.getLogger(__name__)

def _spjoin(*v):
    return ' '.join(map(str, v))

class ArchImpl(Arch):

    ccachepath = shutil.which('ccache')
    staticenv = dict(
        LDLIBS = '-lm',
        USE_CCACHE = '1',
        NDK_CCACHE = ccachepath,
        MAKE = f"make -j{cpu_count()}",
    )
    minbadapi = float('inf')
    MIN_TARGET_API = 26
    MIN_NDK_API = 21

    @types(Config, Platform)
    def __init__(self, config, platform):
        android_api = config.android.api
        assert android_api < self.minbadapi
        if android_api < self.MIN_TARGET_API:
            log.warning("Target API %s < %s", android_api, self.MIN_TARGET_API)
            log.warning('Target APIs lower than 26 are no longer supported on Google Play, and are not recommended. Note that the Target API can be higher than your device Android version, and should usually be as high as possible.')
        self.ndk_api = config.android.ndk_api
        self.container_src = config.container.src
        assert self.ndk_api <= android_api
        if self.ndk_api < self.MIN_NDK_API:
            log.warning("NDK API less than %s is not supported", self.MIN_NDK_API)
        self.cflags = _spjoin(
            '-target',
            self.target(),
            '-fomit-frame-pointer',
            *self.arch_cflags,
        )
        self.cc = _spjoin(self.ccachepath, platform.clang_exe(self), self.cflags)
        strip = f"{self.command_prefix}-strip", '--strip-unneeded'
        self.env = dict(self.staticenv,
            CFLAGS = self.cflags,
            CXXFLAGS = self.cflags,
            LDFLAGS = '', # TODO: Env object.
            CC = self.cc,
            CXX = _spjoin(self.ccachepath, platform.clang_exe(self, plus_plus = True), self.cflags),
            AR = f"{self.command_prefix}-ar",
            RANLIB = f"{self.command_prefix}-ranlib",
            STRIP = _spjoin(*strip),
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
            CPPFLAGS = _spjoin(
                '-DANDROID',
                f"-D__ANDROID_API__={self.ndk_api}",
                f"-I{platform.includepath(self)}",
            ),
        )
        self.strip = Program.text(platform.prebuiltbin(self) / strip[0])[partial](*strip[1:])

    def target(self):
        return f"{self.command_prefix}{self.ndk_api}"

    def builddirname(self):
        return f"{self.name}__ndk_target_{self.ndk_api}"

    def striplibs(self, root):
        log.info("[%s] Strip libs.", root.relative_to(self.container_src))
        self.strip[print](*root.rglob('*.so'))

class BaseArchARM(ArchImpl):

    toolchain_prefix = 'arm-linux-androideabi'
    command_prefix = 'arm-linux-androideabi'
    platform_dir = 'arch-arm'

    def target(self):
        return f"armv7a-linux-androideabi{self.ndk_api}"

class ArchARM(BaseArchARM):

    name = 'armeabi'
    arch_cflags = []
    numver = 1
    minbadapi = 21

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

class Archx86(ArchImpl):

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

class Archx86_64(ArchImpl):

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

class ArchAarch_64(ArchImpl):

    name = 'arm64-v8a'
    toolchain_prefix = 'aarch64-linux-android'
    command_prefix = 'aarch64-linux-android'
    platform_dir = 'arch-arm64'
    arch_cflags = [
        '-march=armv8-a',
    ]
    numver = 8

all_archs = {a.name: a for a in [ArchARM, ArchARMv7_a, Archx86, Archx86_64, ArchAarch_64]}
