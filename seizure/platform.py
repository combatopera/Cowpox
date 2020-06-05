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
from .mirror import Mirror
from diapyr import types
from lagoon import unzip, yes
from lagoon.program import Program
from pathlib import Path
from pkg_resources import parse_version
import logging, re

log = logging.getLogger(__name__)

class Platform:

    @types(Config, Mirror)
    def __init__(self, config, mirror):
        self.android_ndk_version = config.android.ndk
        self.platformname = f"android-{config.android.api}"
        self.acceptlicense = config.android.accept_sdk_license
        self.skip_upd = config.android.skip_update
        self.sdk_dir = Path(config.android_sdk_dir)
        self.ndk_dir = Path(config.android_ndk_dir)
        self.sdkmanager = Program.text(self.sdk_dir / 'tools' / 'bin' / 'sdkmanager')
        self.mirror = mirror

    def _install_android_sdk(self):
        with self.sdk_dir.okorclean() as ok:
            if ok:
                log.info('Android SDK found at %s', self.sdk_dir)
                return
            log.info('Android SDK is missing, downloading')
            archive = self.mirror.download('http://dl.google.com/android/repository/sdk-tools-linux-4333796.zip')
            log.info('Unpacking Android SDK')
            unzip._q.print(archive, cwd = self.sdk_dir)
            log.info('Android SDK tools base installation done.')

    def _install_android_ndk(self):
        with self.ndk_dir.okorclean() as ok:
            if ok:
                log.info('Android NDK found at %s', self.ndk_dir)
                return
            log.info('Android NDK is missing, downloading')
            archive = self.mirror.download(f"https://dl.google.com/android/repository/android-ndk-r{self.android_ndk_version}-linux-x86_64.zip")
            log.info('Unpacking Android NDK')
            unzip._q.print(archive, cwd = self.ndk_dir)
            rootdir, = self.ndk_dir.iterdir()
            for path in rootdir.iterdir():
                path.rename(self.ndk_dir / path.relative_to(rootdir))
            rootdir.rmdir()
            log.info('Android NDK installation done.')

    def _install_android_packages(self):
        log.info('Install/update SDK platform tools.')
        if self.acceptlicense:
            with yes.bg(check = False) as yesproc:
                self.sdkmanager.__licenses.print(stdin = yesproc.stdout)
        self.sdkmanager.tools.platform_tools.print()
        self.sdkmanager.__update.print()
        buildtoolslatest = max(map(parse_version, re.findall(r'\bbuild-tools;(\S+)', self.sdkmanager.__list())))
        buildtoolsactual = max(parse_version(p.name) for p in (self.sdk_dir / 'build-tools').iterdir())
        if buildtoolslatest > buildtoolsactual:
            log.info("Update build-tools to: %s", buildtoolslatest)
            self.sdkmanager.print(f"build-tools;{buildtoolslatest}")
        else:
            log.debug("Already have latest build-tools: %s", buildtoolsactual)
        if not (self.sdk_dir / 'platforms' / self.platformname).exists():
            log.info("Download platform: %s", self.platformname)
            self.sdkmanager.print(f"platforms;{self.platformname}")
        else:
            log.debug("Already have platform: %s", self.platformname)

    def install(self):
        self._install_android_sdk()
        self._install_android_ndk()
        if not self.skip_upd:
            self._install_android_packages()
