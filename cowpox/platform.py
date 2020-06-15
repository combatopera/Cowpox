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
import logging, pickle, re

log = logging.getLogger(__name__)

class Make:

    @types(Config)
    def __init__(self, config):
        self.statepath = Path(config.state.path)
        if self.statepath.exists():
            with self.statepath.open('rb') as f:
                self.targets = pickle.load(f)
        else:
            self.targets = []
        self.cursor = 0

    def __call__(self, target, install = None):
        if self.cursor < len(self.targets):
            if self.targets[self.cursor] == target:
                log.debug("Accept: %s", target)
                self.cursor += 1
                return
            log.debug("Discard: %s", self.targets[self.cursor:])
            del self.targets[self.cursor:]
        if install is None:
            log.debug("Config: %s", target)
        else:
            log.info("Install: %s", target)
            install()
        self.targets.append(target)
        with self.statepath.open('wb') as f:
            pickle.dump(self.targets, f)
        self.cursor += 1

class PlatformInfo:

    @types(Config, Mirror, Make)
    def __init__(self, config, mirror, make):
        self.sdk_dir = Path(config.android_sdk_dir)
        self.skip_update = config.android.skip_update
        self.acceptlicense = config.android.accept_sdk_license
        self.platformname = config.android.platform
        self.ndk_dir = Path(config.android_ndk_dir)
        self.android_ndk_version = config.android.ndk
        self.mirror = mirror
        self.make = make

    def install(self):
        self.make(self.platformname)
        self.make(self.sdk_dir, self._install_android_sdk)
        self.make(self.android_ndk_version)
        self.make(self.ndk_dir, self._install_android_ndk)

    def _install_android_sdk(self):
        self.sdk_dir.clear()
        log.info('Android SDK is missing, downloading')
        archive = self.mirror.download('http://dl.google.com/android/repository/sdk-tools-linux-4333796.zip')
        log.info('Unpacking Android SDK')
        unzip._q.print(archive, cwd = self.sdk_dir)
        log.info('Android SDK tools base installation done.')
        if self.skip_update:
            return
        log.info('Install/update SDK platform tools.')
        sdkmanager = Program.text(self.sdk_dir / 'tools' / 'bin' / 'sdkmanager')
        if self.acceptlicense:
            with yes.bg(check = False) as yesproc:
                sdkmanager.__licenses.print(stdin = yesproc.stdout)
        sdkmanager.tools.platform_tools.print()
        sdkmanager.__update.print()
        buildtoolsdir = self.sdk_dir / 'build-tools'
        actualo, actuals = max([parse_version(p.name), p.name] for p in buildtoolsdir.iterdir()) if buildtoolsdir.exists() else [None, None]
        latesto, latests = max([parse_version(v), v] for v in re.findall(r'\bbuild-tools;(\S+)', sdkmanager.__list()))
        if actualo is None or latesto > actualo:
            log.info("Update build-tools to: %s", latests)
            sdkmanager.print(f"build-tools;{latests}")
        else:
            log.debug("Already have latest build-tools: %s", actuals)
        if not (self.sdk_dir / 'platforms' / self.platformname).exists():
            log.info("Download platform: %s", self.platformname)
            sdkmanager.print(f"platforms;{self.platformname}")
        else:
            log.debug("Already have platform: %s", self.platformname)

    def _install_android_ndk(self):
        self.ndk_dir.clear()
        log.info('Android NDK is missing, downloading')
        archive = self.mirror.download(f"https://dl.google.com/android/repository/android-ndk-r{self.android_ndk_version}-linux-x86_64.zip")
        log.info('Unpacking Android NDK')
        unzip._q.print(archive, cwd = self.ndk_dir)
        rootdir, = self.ndk_dir.iterdir()
        for path in rootdir.iterdir():
            path.rename(self.ndk_dir / path.relative_to(rootdir))
        rootdir.rmdir()
        log.info('Android NDK installation done.')

class Platform:

    @types(Config, PlatformInfo)
    def __init__(self, config, info):
        self.sdk_dir = Path(config.android_sdk_dir)
        self.ndk_dir = Path(config.android_ndk_dir)
        self.ndk_api = config.android.ndk_api
        info.install()

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

    def toolchain_version(self, arch):
        prefix = f"{arch.toolchain_prefix}-"
        toolchain_path = self.ndk_dir / 'toolchains'
        if not toolchain_path.is_dir():
            raise Exception('Could not find toolchain subdirectory!')
        versions = [path.name[len(prefix):] for path in toolchain_path.glob(f"{prefix}*")]
        if not versions:
            log.warning("Could not find any toolchain for %s!", arch.toolchain_prefix)
            raise Exception('python-for-android cannot continue due to the missing executables above')
        versions.sort()
        log.info("Found the following toolchain versions: %s", versions)
        version = [v for v in versions if v[0].isdigit()][-1]
        log.info("Picking the latest gcc toolchain, here %s", version)
        return version

    def ndk_platform(self, arch):
        ndk_platform = self.ndk_dir / 'platforms' / f"android-{self.ndk_api}" / arch.platform_dir
        if not ndk_platform.exists():
            raise Exception(f"ndk_platform doesn't exist: {ndk_platform}")
        return ndk_platform

    def clang_path(self, arch):
        llvm_dir, = (self.ndk_dir / 'toolchains').glob('llvm*')
        return llvm_dir / 'prebuilt' / arch.build_platform / 'bin'

    def clang_exe(self, arch, with_target = False, plus_plus = False):
        return self.clang_path(arch) / f"""{f"{arch.target()}-" if with_target else ''}clang{'++' if plus_plus else ''}"""

    def includepath(self, arch):
        return self.ndk_dir / 'sysroot' / 'usr' / 'include' / arch.command_prefix

    def prebuiltbin(self, arch):
        return self.ndk_dir / 'toolchains' / f"{arch.toolchain_prefix}-{self.toolchain_version(arch)}" / 'prebuilt' / 'linux-x86_64' / 'bin'
