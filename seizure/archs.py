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

from lagoon import which
from multiprocessing import cpu_count
from pathlib import Path
import os

class Arch:

    build_platform = f"{os.uname()[0]}-{os.uname()[-1]}".lower()
    common_cflags = [
        '-target {target}',
        '-fomit-frame-pointer',
    ]
    common_ldflags = ['-L{ctx_libs_dir}']
    common_ldlibs = ['-lm']
    common_ldshared = [
        '-pthread',
        '-shared',
        '-Wl,-O1',
        '-Wl,-Bsymbolic-functions',
    ]
    ccachepath, = which('ccache').splitlines()

    def __init__(self, config, ctx):
        self.ndk_api = config.android.ndk_api
        self.ndk_dir = Path(config.android_ndk_dir)
        self.ctx = ctx

    def __str__(self): # TODO: Retire.
        return self.name

    def target(self):
        return f"{self.command_prefix}{self.ndk_api}"

    def _clang_path(self):
        llvm_dir, = (self.ndk_dir / 'toolchains').glob('llvm*')
        return llvm_dir / 'prebuilt' / self.build_platform / 'bin'

    def get_clang_exe(self, with_target = False, plus_plus = False):
        return self._clang_path() / f"""{f"{self.target()}-" if with_target else ''}clang{'++' if plus_plus else ''}"""

    def get_env(self, ctx):
        env = {}
        env['CFLAGS'] = ' '.join(self.common_cflags).format(target=self.target())
        if self.arch_cflags:
            env['CFLAGS'] += ' ' + ' '.join(self.arch_cflags)
        env['CXXFLAGS'] = env['CFLAGS']
        env['CPPFLAGS'] = ' '.join([
            '-DANDROID',
            f"-D__ANDROID_API__={self.ndk_api}",
            f"-I{self.ndk_dir / 'sysroot' / 'usr' / 'include' / self.command_prefix}",
            f"""-I{ctx.get_python_install_dir() / 'include' / f"python{ctx.python_recipe.version[:3]}"}""",
        ])
        env['LDFLAGS'] = '  ' + ' '.join(self.common_ldflags).format(ctx_libs_dir=ctx.get_libs_dir(self))
        env['LDLIBS'] = ' '.join(self.common_ldlibs)
        env['USE_CCACHE'] = '1'
        env['NDK_CCACHE'] = self.ccachepath
        env.update({k: v for k, v in os.environ.items() if k.startswith('CCACHE_')})
        env['CC'] = f"{self.ccachepath} {self.get_clang_exe()} {env['CFLAGS']}"
        env['CXX'] = f"{self.ccachepath} {self.get_clang_exe(plus_plus = True)} {env['CXXFLAGS']}"
        env['AR'] = f"{self.command_prefix}-ar"
        env['RANLIB'] = f"{self.command_prefix}-ranlib"
        env['STRIP'] = f"{self.command_prefix}-strip --strip-unneeded"
        env['MAKE'] = f"make -j{cpu_count()}"
        env['READELF'] = f"{self.command_prefix}-readelf"
        env['NM'] = f"{self.command_prefix}-nm"
        env['LD'] = f"{self.command_prefix}-ld"
        env['ARCH'] = self.name
        env['NDK_API'] = f"android-{self.ndk_api}"
        env['TOOLCHAIN_PREFIX'] = ctx.toolchain_prefix
        env['TOOLCHAIN_VERSION'] = ctx.toolchain_version
        env['LDSHARED'] = env['CC'] + ' ' + ' '.join(self.common_ldshared)
        env['BUILDLIB_PATH'] = ctx.get_recipe(f"host{ctx.python_recipe.name}").get_build_dir(self) / 'native-build' / 'build' / f"lib.{self.build_platform}-{ctx.python_recipe.major_minor_version_string}"
        env['PATH'] = f"{self._clang_path()}{os.pathsep}{os.environ['PATH']}"
        return env

class BaseArchARM(Arch):

    toolchain_prefix = 'arm-linux-androideabi'
    command_prefix = 'arm-linux-androideabi'
    platform_dir = 'arch-arm'

    def target(self):
        return f"armv7a-linux-androideabi{self.ndk_api}"

class ArchARM(BaseArchARM):

    name = "armeabi"
    arch_cflags = []

class ArchARMv7_a(BaseArchARM):

    name = 'armeabi-v7a'
    arch_cflags = [
        '-march=armv7-a',
        '-mfloat-abi=softfp',
        '-mfpu=vfp',
        '-mthumb',
        '-fPIC',
    ]

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

class ArchAarch_64(Arch):

    name = 'arm64-v8a'
    toolchain_prefix = 'aarch64-linux-android'
    command_prefix = 'aarch64-linux-android'
    platform_dir = 'arch-arm64'
    arch_cflags = [
        '-march=armv8-a',
    ]

all_archs = {a.name: a for a in [ArchARM, ArchARMv7_a, Archx86, Archx86_64, ArchAarch_64]}
