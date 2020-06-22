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

from glob import glob
from lagoon import which
from multiprocessing import cpu_count
from os.path import join
from p4a import Recipe
import os

class Arch:

    common_cflags = [
        '-target {target}',
        '-fomit-frame-pointer',
    ]
    common_cppflags = [
        '-DANDROID',
        '-D__ANDROID_API__={ctx.ndk_api}',
        '-I{ctx.ndk_dir}/sysroot/usr/include/{command_prefix}',
        '-I{python_includes}',
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

    def __init__(self, ctx):
        self.ctx = ctx

    def __str__(self):
        return self.arch

    @property
    def include_dirs(self):
        return [
            "{}/{}".format(
                self.ctx.include_dir,
                d.format(arch=self))
            for d in self.ctx.include_dirs]

    @property
    def target(self):
        # As of NDK r19, the toolchains installed by default with the
        # NDK may be used in-place. The make_standalone_toolchain.py script
        # is no longer needed for interfacing with arbitrary build systems.
        # See: https://developer.android.com/ndk/guides/other_build_systems
        return '{triplet}{ndk_api}'.format(
            triplet=self.command_prefix, ndk_api=self.ctx.ndk_api
        )

    @property
    def clang_path(self):
        llvm_dirname = os.path.basename(glob(str(self.ctx.ndk_dir / 'toolchains' / 'llvm*'))[-1])
        return self.ctx.ndk_dir / 'toolchains' / llvm_dirname / 'prebuilt' / Recipe.build_platform / 'bin'

    @property
    def clang_exe(self):
        return self.get_clang_exe()

    @property
    def clang_exe_cxx(self):
        return self.get_clang_exe(plus_plus=True)

    def get_clang_exe(self, with_target = False, plus_plus = False):
        return self.clang_path / f"""{f"{self.target}-" if with_target else ''}clang{'++' if plus_plus else ''}"""

    def get_env(self, with_flags_in_cc=True):
        env = {}
        env['CFLAGS'] = ' '.join(self.common_cflags).format(target=self.target)
        if self.arch_cflags:
            env['CFLAGS'] += ' ' + ' '.join(self.arch_cflags)
        env['CXXFLAGS'] = env['CFLAGS']
        env['CPPFLAGS'] = ' '.join(self.common_cppflags).format(
            ctx=self.ctx,
            command_prefix=self.command_prefix,
            python_includes=join(
                self.ctx.get_python_install_dir(),
                'include/python{}'.format(self.ctx.python_recipe.version[0:3]),
            ),
        )
        env['LDFLAGS'] = '  ' + ' '.join(self.common_ldflags).format(ctx_libs_dir=self.ctx.get_libs_dir(self.arch))
        env['LDLIBS'] = ' '.join(self.common_ldlibs)
        if int(os.environ.get('USE_CCACHE', '1')):
            ccache = f"{self.ccachepath} "
            env['USE_CCACHE'] = '1'
            env['NDK_CCACHE'] = self.ccachepath
            env.update({k: v for k, v in os.environ.items() if k.startswith('CCACHE_')})
        else:
            ccache = ''
        if with_flags_in_cc:
            env['CC'] = f"{ccache}{self.clang_exe} {env['CFLAGS']}"
            env['CXX'] = f"{ccache}{self.clang_exe_cxx} {env['CXXFLAGS']}"
        else:
            env['CC'] = f"{ccache}{self.clang_exe}"
            env['CXX'] = f"{ccache}{self.clang_exe_cxx}"
        env['AR'] = f"{self.command_prefix}-ar"
        env['RANLIB'] = f"{self.command_prefix}-ranlib"
        env['STRIP'] = f"{self.command_prefix}-strip --strip-unneeded"
        env['MAKE'] = f"make -j{cpu_count()}"
        env['READELF'] = f"{self.command_prefix}-readelf"
        env['NM'] = f"{self.command_prefix}-nm"
        env['LD'] = f"{self.command_prefix}-ld"
        env['ARCH'] = self.arch
        env['NDK_API'] = f"android-{self.ctx.ndk_api}"
        env['TOOLCHAIN_PREFIX'] = self.ctx.toolchain_prefix
        env['TOOLCHAIN_VERSION'] = self.ctx.toolchain_version
        env['LDSHARED'] = env['CC'] + ' ' + ' '.join(self.common_ldshared)
        hostpython_recipe = self.ctx.get_recipe(f"host{self.ctx.python_recipe.name}")
        env['BUILDLIB_PATH'] = hostpython_recipe.get_build_dir(self.arch) / 'native-build' / 'build' / f"lib.{Recipe.build_platform}-{self.ctx.python_recipe.major_minor_version_string}"
        env['PATH'] = f"{self.clang_path}{os.pathsep}{os.environ['PATH']}"
        return env

class BaseArchARM(Arch):

    toolchain_prefix = 'arm-linux-androideabi'
    command_prefix = 'arm-linux-androideabi'
    platform_dir = 'arch-arm'

    @property
    def target(self):
        target_data = self.command_prefix.split('-')
        return '{triplet}{ndk_api}'.format(
            triplet='-'.join(['armv7a', target_data[1], target_data[2]]),
            ndk_api=self.ctx.ndk_api,
        )

class ArchARM(BaseArchARM):

    arch = "armeabi"
    arch_cflags = []

class ArchARMv7_a(BaseArchARM):

    arch = 'armeabi-v7a'
    arch_cflags = [
        '-march=armv7-a',
        '-mfloat-abi=softfp',
        '-mfpu=vfp',
        '-mthumb',
        '-fPIC',
    ]

class Archx86(Arch):

    arch = 'x86'
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

    arch = 'x86_64'
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

    arch = 'arm64-v8a'
    toolchain_prefix = 'aarch64-linux-android'
    command_prefix = 'aarch64-linux-android'
    platform_dir = 'arch-arm64'
    arch_cflags = [
        '-march=armv8-a',
    ]

all_archs = ArchARM, ArchARMv7_a, Archx86, Archx86_64, ArchAarch_64
