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
from .libs.version import parse
from .mirror import Mirror
from diapyr import types
from lagoon import unzip, yes
from lagoon.program import Program
from pathlib import Path
import logging

log = logging.getLogger(__name__)

class Platform:

    @types(Config, Mirror)
    def __init__(self, config, mirror):
        self.android_ndk_version = config.android.ndk
        self.android_api = config.android.api
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

    def _android_list_build_tools_versions(self):
        for line in (l.strip() for l in self.sdkmanager.__list().split('\n')):
            if line.startswith('build-tools;'):
                package_name = line.split(' ')[0]
                assert package_name.count(';') == 1, f'could not parse package "{package_name}"'
                yield parse(package_name.split(';')[1])

    def _android_update_sdk(self, *args):
        if self.acceptlicense:
            with yes.bg(check = False) as yesproc:
                self.sdkmanager.__licenses.print(stdin = yesproc.stdout)
        self.sdkmanager.print(*args)

    @staticmethod
    def _read_version_subdir(path):
        versions = []
        if not path.exists():
            log.debug("build-tools folder not found %s", path)
            return parse("0")
        for v in (p.name for p in path.iterdir()):
            try:
                versions.append(parse(v))
            except:
                pass
        if not versions:
            log.error('Unable to find the latest version for %s', path)
            return parse("0")
        return max(versions)

    def _install_android_packages(self):
        log.info('Installing/updating SDK platform tools if necessary')
        self._android_update_sdk('tools', 'platform-tools')
        self._android_update_sdk('--update')
        log.info('Updating SDK build tools if necessary')
        available_v_build_tools = list(self._android_list_build_tools_versions())
        if not available_v_build_tools:
            log.error('Did not find any build tools available to download')
        latest_v_build_tools = max(available_v_build_tools)
        if latest_v_build_tools > self._read_version_subdir(self.sdk_dir / 'build-tools'):
            self._android_update_sdk(f"build-tools;{latest_v_build_tools}")
        log.info('Downloading platform api target if necessary')
        if not (self.sdk_dir / 'platforms' / f"android-{self.android_api}").exists():
            self.sdkmanager.print(f"platforms;android-{self.android_api}")
        log.info('Android packages installation done.')

    def install(self):
        self._install_android_sdk()
        self._install_android_ndk()
        if not self.skip_upd:
            self._install_android_packages()
