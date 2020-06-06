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
from distutils.version import LooseVersion
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
        buildtoolsdir = self.sdk_dir / 'build-tools'
        actualo, actuals = max([parse_version(p.name), p.name] for p in buildtoolsdir.iterdir()) if buildtoolsdir.exists() else [None, None]
        latesto, latests = max([parse_version(v), v] for v in re.findall(r'\bbuild-tools;(\S+)', self.sdkmanager.__list()))
        if actualo is None or latesto > actualo:
            log.info("Update build-tools to: %s", latests)
            self.sdkmanager.print(f"build-tools;{latests}")
        else:
            log.debug("Already have latest build-tools: %s", actuals)
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

    def build_tools_version(self):
        ignored = {'.DS_Store', '.ds_store'}
        return max((p.name for p in (self.sdk_dir / 'build-tools').iterdir() if p.name not in ignored), key = LooseVersion)

    def apilevels(self):
        avdmanagerpath = self.sdk_dir / 'tools' / 'bin' / 'avdmanager'
        if avdmanagerpath.exists():
            targets = Program.text(avdmanagerpath)('list', 'target').split('\n')
        elif (self.sdk_dir / 'tools' / 'android').exists():
            android = Program.text(self.sdk_dir / 'tools' / 'android')
            targets = android.list().split('\n')
        else:
            raise Exception('Could not find `android` or `sdkmanager` binaries in Android SDK', 'Make sure the path to the Android SDK is correct')
        apis = [s for s in targets if re.match(r'^ *API level: ', s)]
        apis = [re.findall(r'[0-9]+', s) for s in apis]
        return [int(s[0]) for s in apis if s]

    def get_toolchain_versions(self, arch):
        toolchain_versions = []
        toolchain_path_exists = True
        prefix = f"{arch.toolchain_prefix}-"
        toolchain_path = self.ndk_dir / 'toolchains'
        if toolchain_path.is_dir():
            toolchain_contents = toolchain_path.glob(f"{prefix}*")
            toolchain_versions = [path.name[len(prefix):] for path in toolchain_contents]
        else:
            log.warning('Could not find toolchain subdirectory!')
            toolchain_path_exists = False
        return toolchain_versions, toolchain_path_exists

    def get_ndk_platform_dir(self, ndk_api, arch):
        ndk_platform_dir_exists = True
        ndk_platform = self.ndk_dir / 'platforms' / f"android-{ndk_api}" / arch.platform_dir
        if not ndk_platform.exists():
            log.warning("ndk_platform doesn't exist: %s", ndk_platform)
            ndk_platform_dir_exists = False
        return ndk_platform, ndk_platform_dir_exists
