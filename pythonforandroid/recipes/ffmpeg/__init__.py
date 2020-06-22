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

from os.path import exists, join, realpath
from pythonforandroid.logger import shprint
from p4a import Recipe
import sh

class FFMpegRecipe(Recipe):

    version = '007e03348dbd8d3de3eb09022d72c734a8608144'
    # Moved to github.com instead of ffmpeg.org to improve download speed
    url = 'https://github.com/FFmpeg/FFmpeg/archive/{version}.zip'
    depends = ['sdl2']  # Need this to build correct recipe order
    opts_depends = ['openssl', 'ffpyplayer_codecs']
    patches = ['patches/configure.patch']

    def should_build(self, arch):
        build_dir = self.get_build_dir(arch.arch)
        return not exists(join(build_dir, 'lib', 'libavcodec.so'))

    def prebuild_arch(self, arch):
        self.apply_patches(arch)

    def get_recipe_env(self, arch):
        env = super(FFMpegRecipe, self).get_recipe_env(arch)
        env['NDK'] = self.ctx.ndk_dir
        return env

    def build_arch(self, arch):
        with self.current_directory(self.get_build_dir(arch.arch)):
            env = arch.get_env()

            flags = ['--disable-everything']
            cflags = []
            ldflags = []

            if 'openssl' in self.ctx.recipe_build_order:
                flags += [
                    '--enable-openssl',
                    '--enable-nonfree',
                    '--enable-protocol=https,tls_openssl',
                ]
                build_dir = self.get_recipe('openssl').get_build_dir(arch.arch)
                cflags += ['-I' + build_dir + '/include/',
                           '-DOPENSSL_API_COMPAT=0x10002000L']
                ldflags += ['-L' + build_dir]

            if 'ffpyplayer_codecs' in self.ctx.recipe_build_order:
                # libx264
                flags += ['--enable-libx264']
                build_dir = self.get_recipe('libx264').get_build_dir(arch.arch)
                cflags += ['-I' + build_dir + '/include/']
                ldflags += ['-lx264', '-L' + build_dir + '/lib/']

                # libshine
                flags += ['--enable-libshine']
                build_dir = self.get_recipe('libshine').get_build_dir(arch.arch)
                cflags += ['-I' + build_dir + '/include/']
                ldflags += ['-lshine', '-L' + build_dir + '/lib/']
                ldflags += ['-lm']

                # Enable all codecs:
                flags += [
                    '--enable-parsers',
                    '--enable-decoders',
                    '--enable-encoders',
                    '--enable-muxers',
                    '--enable-demuxers',
                ]
            else:
                # Enable codecs only for .mp4:
                flags += [
                    '--enable-parser=aac,ac3,h261,h264,mpegaudio,mpeg4video,mpegvideo,vc1',
                    '--enable-decoder=aac,h264,mpeg4,mpegvideo',
                    '--enable-muxer=h264,mov,mp4,mpeg2video',
                    '--enable-demuxer=aac,h264,m4v,mov,mpegvideo,vc1',
                ]

            # needed to prevent _ffmpeg.so: version node not found for symbol av_init_packet@LIBAVFORMAT_52
            # /usr/bin/ld: failed to set dynamic section sizes: Bad value
            flags += [
                '--disable-symver',
            ]

            # disable binaries / doc
            flags += [
                '--disable-programs',
                '--disable-doc',
            ]

            # other flags:
            flags += [
                '--enable-filter=aresample,resample,crop,adelay,volume,scale',
                '--enable-protocol=file,http,hls',
                '--enable-small',
                '--enable-hwaccels',
                '--enable-gpl',
                '--enable-pic',
                '--disable-static',
                '--disable-debug',
                '--enable-shared',
            ]

            if 'arm64' in arch.arch:
                cross_prefix = 'aarch64-linux-android-'
                arch_flag = 'aarch64'
            else:
                cross_prefix = 'arm-linux-androideabi-'
                arch_flag = 'arm'

            # android:
            flags += [
                '--target-os=android',
                '--enable-cross-compile',
                '--cross-prefix={}-'.format(arch.target),
                '--arch={}'.format(arch_flag),
                '--strip={}strip'.format(cross_prefix),
                '--sysroot={}'.format(join(self.ctx.ndk_dir, 'toolchains',
                                           'llvm', 'prebuilt', 'linux-x86_64',
                                           'sysroot')),
                '--enable-neon',
                '--prefix={}'.format(realpath('.')),
            ]

            if arch_flag == 'arm':
                cflags += [
                    '-mfpu=vfpv3-d16',
                    '-mfloat-abi=softfp',
                    '-fPIC',
                ]

            env['CFLAGS'] += ' ' + ' '.join(cflags)
            env['LDFLAGS'] += ' ' + ' '.join(ldflags)

            configure = sh.Command('./configure')
            shprint(configure, *flags, _env=env)
            shprint(sh.make, '-j4', _env=env)
            shprint(sh.make, 'install', _env=env)
            # copy libs:
            sh.cp('-a', sh.glob('./lib/lib*.so'),
                  self.ctx.get_libs_dir(arch.arch))

