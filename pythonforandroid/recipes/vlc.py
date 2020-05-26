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

from os.path import join, isdir, isfile
from pythonforandroid.logger import shprint
from p4a import Recipe
from pythonforandroid.util import current_directory
import logging, os, sh

log = logging.getLogger(__name__)

class VlcRecipe(Recipe):

    version = '3.0.0'
    url = None
    name = 'vlc'
    depends = []
    port_git = 'http://git.videolan.org/git/vlc-ports/android.git'
#    vlc_git = 'http://git.videolan.org/git/vlc.git'
    ENV_LIBVLC_AAR = 'LIBVLC_AAR'
    aars = {}  # for future use of multiple arch

    def prebuild_arch(self, arch):
        super(VlcRecipe, self).prebuild_arch(arch)
        build_dir = self.get_build_dir(arch.arch)
        port_dir = join(build_dir, 'vlc-port-android')
        if self.ENV_LIBVLC_AAR in os.environ:
            aar = os.environ.get(self.ENV_LIBVLC_AAR)
            if isdir(aar):
                aar = join(aar, 'libvlc-{}.aar'.format(self.version))
            if not isfile(aar):
                log.warning("Error: %s is not valid libvlc-<ver>.aar bundle", aar)
                log.info("check %s environment!", self.ENV_LIBVLC_AAR)
                exit(1)
            self.aars[arch] = aar
        else:
            aar_path = join(port_dir, 'libvlc', 'build', 'outputs', 'aar')
            self.aars[arch] = aar = join(aar_path, 'libvlc-{}.aar'.format(self.version))
            log.warning("HINT: set path to precompiled libvlc-<ver>.aar bundle in %s environment!", self.ENV_LIBVLC_AAR)
            log.info("libvlc-<ver>.aar should build from sources at %s", port_dir)
            if not isfile(join(port_dir, 'compile.sh')):
                log.info("clone vlc port for android sources from %s", self.port_git)
                shprint(sh.git, 'clone', self.port_git, port_dir,
                        _tail=20, _critical=True)
# now "git clone ..." is a part of compile.sh
#            vlc_dir = join(port_dir, 'vlc')
#            if not isfile(join(vlc_dir, 'Makefile.am')):
#                info("clone vlc sources from {}".format(self.vlc_git))
#                shprint(sh.git, 'clone', self.vlc_git, vlc_dir,
#                            _tail=20, _critical=True)

    def build_arch(self, arch):
        super(VlcRecipe, self).build_arch(arch)
        build_dir = self.get_build_dir(arch.arch)
        port_dir = join(build_dir, 'vlc-port-android')
        aar = self.aars[arch]
        if not isfile(aar):
            with current_directory(port_dir):
                env = dict(os.environ)
                env.update({
                    'ANDROID_ABI': arch.arch,
                    'ANDROID_NDK': self.ctx.ndk_dir,
                    'ANDROID_SDK': self.ctx.sdk_dir,
                })
                log.info('compiling vlc from sources')
                log.debug("environment: %s", env)
                if not isfile(join('bin', 'VLC-debug.apk')):
                    shprint(sh.Command('./compile.sh'), _env=env,
                            _tail=50, _critical=True)
                shprint(sh.Command('./compile-libvlc.sh'), _env=env,
                        _tail=50, _critical=True)
        shprint(sh.cp, '-a', aar, self.ctx.aars_dir)

