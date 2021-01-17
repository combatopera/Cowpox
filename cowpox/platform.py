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

from .make import Make
from .mirror import Mirror
from .util import build_platform
from aridity.config import Config
from diapyr import types
from distutils.version import LooseVersion
from jproperties import Properties
from lagoon import unzip
from lagoon.program import bg, partial, Program
from pathlib import Path
from pkg_resources import parse_version # XXX: Why not LooseVersion?
import logging, re, subprocess, sys, time

log = logging.getLogger(__name__)

class PlatformMemo: pass

class PlatformInfo:

    @types(Config, Mirror)
    def __init__(self, config, mirror):
        self.sdk_dir = Path(config.SDK.dir)
        self.skip_update = config.android.skip_update
        self.accept_licenses = config.SDK.accept.licenses
        self.platformname = config.android.platform
        self.ndk_dir = Path(config.NDK.dir)
        self.android_ndk_version = config.android.ndk
        self.mirror = mirror

    @types(Make, this = PlatformMemo)
    def install(self, make):
        return [
            make(self.sdk_dir, [self.skip_update, self.platformname], self._install_android_sdk),
            make(self.ndk_dir, self.android_ndk_version, self._install_android_ndk),
        ]

    @staticmethod
    def _print(partial):
        'Elide redundant CR-terminated updates to reduce spamminess in GitHub Actions.'
        target = sys.stderr # Avoid sys.stdout as it is likely to be fully buffered.
        flush = lambda *lines: [*map(target.write, lines), target.flush()] # Consistent with StreamHandler.
        with partial[bg]() as f:
            unwritten = ''
            oktime = time.time()
            for line in f:
                now = time.time()
                if 40 < len(line) and '[' == line[0] and ']' == line[40]:
                    if now >= oktime:
                        flush(line)
                        unwritten = ''
                        oktime = now + 1
                    else:
                        unwritten = line
                else:
                    flush(unwritten, line)
                    unwritten = ''
                    oktime = now
            flush(unwritten)

    def _install_android_sdk(self):
        log.info('Android SDK is missing, downloading')
        archive = self.mirror.download('http://dl.google.com/android/repository/sdk-tools-linux-4333796.zip')
        log.info('Unpacking Android SDK')
        self.sdk_dir.mkdir()
        unzip._q[print](archive, cwd = self.sdk_dir)
        log.info('Android SDK tools base installation done.')
        if self.skip_update:
            return
        log.info('Install/update SDK platform tools.')
        sdkmanager = Program.text(self.sdk_dir / 'tools' / 'bin' / 'sdkmanager')
        if self.accept_licenses:
            try:
                with sdkmanager.__licenses[bg](stdin = subprocess.PIPE, stdout = subprocess.DEVNULL) as stdin:
                    while True:
                        print('y', file = stdin)
            except BrokenPipeError:
                pass
        self._print(sdkmanager.tools.platform_tools)
        self._print(sdkmanager.__update)
        buildtoolsdir = self.sdk_dir / 'build-tools'
        actualo, actuals = max([parse_version(p.name), p.name] for p in buildtoolsdir.iterdir()) if buildtoolsdir.exists() else [None, None]
        latesto, latests = max([parse_version(v), v] for v in re.findall(r'\bbuild-tools;(\S+)', sdkmanager.__list()))
        if actualo is None or latesto > actualo:
            log.info("Update build-tools to: %s", latests)
            self._print(sdkmanager[partial](f"build-tools;{latests}"))
        else:
            log.debug("Already have latest build-tools: %s", actuals)
        if not (self.sdk_dir / 'platforms' / self.platformname).exists():
            log.info("Download platform: %s", self.platformname)
            self._print(sdkmanager[partial](f"platforms;{self.platformname}"))
        else:
            log.debug("Already have platform: %s", self.platformname)

    def _install_android_ndk(self):
        log.info('Android NDK is missing, downloading')
        archive = self.mirror.download(f"https://dl.google.com/android/repository/android-ndk-r{self.android_ndk_version}-linux-x86_64.zip")
        log.info('Unpacking Android NDK')
        self.ndk_dir.mkdir()
        unzip._q[print](archive, cwd = self.ndk_dir)
        rootdir, = self.ndk_dir.iterdir()
        for path in rootdir.iterdir():
            path.rename(self.ndk_dir / path.relative_to(rootdir))
        rootdir.rmdir()
        log.info('Android NDK installation done.')

class Platform:

    MIN_NDK_VERSION = 19
    MAX_NDK_VERSION = 20

    @staticmethod
    def _ndkversionstr(version):
        minor = version[1]
        return f"{version[0]}{chr(ord('a') + minor) if minor else ''}"

    @types(Config, PlatformMemo)
    def __init__(self, config, memo):
        self.sdk_dir = Path(config.SDK.dir)
        self.ndk_dir = Path(config.NDK.dir)
        self.ndk_api = config.android.ndk_api
        android_api = config.android.api
        apis = self._apilevels()
        log.info("Available Android APIs are (%s)", ', '.join(map(str, apis)))
        assert android_api in apis
        log.info("Requested API target %s is available, continuing.", android_api)
        version = self._read_ndk_version()
        log.info("Found NDK version %s", self._ndkversionstr(version))
        major_version = version[0]
        assert major_version >= self.MIN_NDK_VERSION
        if major_version > self.MAX_NDK_VERSION:
            log.warning('Newer NDKs may not be fully supported by p4a.')
        self.ndk_build = Program.text(self.ndk_dir / 'ndk-build')[partial]('V=1')
        self.memo = memo

    def build_tools_version(self):
        ignored = {'.DS_Store', '.ds_store'}
        return max((p.name for p in (self.sdk_dir / 'build-tools').iterdir() if p.name not in ignored), key = LooseVersion)

    def _apilevels(self):
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

    def _read_ndk_version(self):
        p = Properties()
        with (self.ndk_dir / 'source.properties').open('rb') as f:
            p.load(f)
        return LooseVersion(p['Pkg.Revision'].data).version

    def toolchain_version(self, arch): # TODO: Do not execute twice.
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
        return llvm_dir / 'prebuilt' / build_platform / 'bin'

    def clang_exe(self, arch, with_target = False, plus_plus = False):
        return self.clang_path(arch) / f"""{f"{arch.target()}-" if with_target else ''}clang{'++' if plus_plus else ''}"""

    def includepath(self, arch):
        return self.ndk_dir / 'sysroot' / 'usr' / 'include' / arch.command_prefix

    def prebuiltbin(self, arch):
        return self.ndk_dir / 'toolchains' / f"{arch.toolchain_prefix}-{self.toolchain_version(arch)}" / 'prebuilt' / 'linux-x86_64' / 'bin'
