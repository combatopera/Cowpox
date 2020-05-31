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

from .config import Config, LegacyConfig
from .dirs import Dirs
from .distribution import generate_dist_folder_name
from .jsonstore import JsonStore
from .libs.version import parse
from .mirror import download
from .p4a import create, makeapk
from diapyr import types
from lagoon import tar, unzip, yes
from lagoon.program import Program
from pathlib import Path
from types import SimpleNamespace
import logging, os, shutil

log = logging.getLogger(__name__)

class TargetAndroid:

    @types(Config, LegacyConfig, JsonStore, Dirs)
    def __init__(self, config, legacyconfig, state, dirs):
        self.APACHE_ANT_VERSION = config.APACHE_ANT_VERSION
        self.android_ndk_version = config.android.ndk
        self.workspace = Path(config.container.workspace)
        self.android_api = config.android.api
        self.android_minapi = config.android.minapi
        self.arch = config.android.arch
        self.dist_name = config.package.name
        self.bootstrapname = config.p4a.bootstrap
        self.acceptlicense = config.android.accept_sdk_license
        self.skip_upd = config.android.skip_update
        self.ndk_api = config.android.ndk_api
        self.requirements = list(config.requirements)
        self.fqpackage = config.package.fq
        self.build_mode = config.build_mode
        self.p4a_whitelist = list(config.android.whitelist)
        self.permissions = list(config.android.permissions)
        self.orientation = config.orientation
        self.meta_data = config.android.meta_data.copy()
        self.sdkmanager = Program.text(dirs.android_sdk_dir / 'tools' / 'bin' / 'sdkmanager').partial(cwd = dirs.android_sdk_dir)
        self.build_dir = dirs.platform_dir / f"build-{self.arch}"
        self.config = legacyconfig
        self.state = state
        self.dirs = dirs

    def _install_apache_ant(self):
        ant_dir = self.dirs.apache_ant_dir
        if ant_dir.exists():
            log.info('Apache ANT found at %s', ant_dir)
            return
        ant_dir.mkdir(parents = True)
        log.info('Android ANT is missing, downloading')
        archive = f"apache-ant-{self.APACHE_ANT_VERSION}-bin.tar.gz"
        download('http://archive.apache.org/dist/ant/binaries/', archive, ant_dir)
        tar.xzf.print(archive, cwd = ant_dir)
        log.info('Apache ANT installation done.')

    def _install_android_sdk(self):
        sdk_dir = self.dirs.android_sdk_dir
        if sdk_dir.exists():
            log.info('Android SDK found at %s', sdk_dir)
            return
        log.info('Android SDK is missing, downloading')
        archive = 'sdk-tools-linux-4333796.zip'
        sdk_dir.mkdir(parents = True)
        download('http://dl.google.com/android/repository/', archive, sdk_dir)
        log.info('Unpacking Android SDK')
        unzip._q.print(archive, cwd = sdk_dir)
        log.info('Android SDK tools base installation done.')

    def _install_android_ndk(self):
        ndk_dir = self.dirs.android_ndk_dir
        if ndk_dir.exists():
            log.info('Android NDK found at %s', ndk_dir)
            return
        log.info('Android NDK is missing, downloading')
        archive = f"android-ndk-r{self.android_ndk_version}-linux-x86_64.zip"
        download('https://dl.google.com/android/repository/', archive, self.dirs.global_platform_dir)
        log.info('Unpacking Android NDK')
        unzip._q.print(archive, cwd = self.dirs.global_platform_dir)
        source = self.dirs.global_platform_dir / f"android-ndk-r{self.android_ndk_version}"
        log.debug('Rename %s to %s', source, ndk_dir)
        shutil.move(source, ndk_dir)
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
        cache_key = 'android:sdk_installation'
        cache_value = [
            str(self.android_api), str(self.android_minapi), self.android_ndk_version,
            str(self.dirs.android_sdk_dir), str(self.dirs.android_ndk_dir),
        ]
        if self.state.get(cache_key, None) == cache_value:
            return
        if not self.skip_upd:
            log.info('Installing/updating SDK platform tools if necessary')
            self._android_update_sdk('tools', 'platform-tools')
            self._android_update_sdk('--update')
        else:
            log.info('Skipping Android SDK update due to spec file setting')
            log.info('Note: this also prevents installing missing SDK components')
        log.info('Updating SDK build tools if necessary')
        available_v_build_tools = list(self._android_list_build_tools_versions())
        if not available_v_build_tools:
            log.error('Did not find any build tools available to download')
        latest_v_build_tools = max(available_v_build_tools)
        if latest_v_build_tools > self._read_version_subdir(self.dirs.android_sdk_dir / 'build-tools'):
            if not self.skip_upd:
                self._android_update_sdk(f"build-tools;{latest_v_build_tools}")
            else:
                log.info('Skipping update to build tools %s due to spec setting', latest_v_build_tools)
        log.info('Downloading platform api target if necessary')
        if not (self.dirs.android_sdk_dir / 'platforms' / f"android-{self.android_api}").exists():
            if not self.skip_upd:
                self.sdkmanager.print(f"platforms;android-{self.android_api}")
            else:
                log.info('Skipping install API %s platform tools due to spec setting', self.android_api)
        log.info('Android packages installation done.')
        self.state[cache_key] = cache_value
        self.state.sync()

    def install_platform(self):
        self._install_apache_ant()
        self._install_android_sdk()
        self._install_android_ndk()
        self._install_android_packages()

    def compile_platform(self):
        create(
            self.dirs.android_sdk_dir,
            self.dirs.android_ndk_dir,
            self.android_api,
            self.dist_name,
            self.bootstrapname,
            self.arch,
            self.build_dir,
            self.ndk_api,
            self.workspace / 'local_recipes',
            self.requirements,
        )

    def _get_dist_dir(self):
        expected_dist_name = generate_dist_folder_name(self.dist_name, arch_names = [self.arch])
        expected_dist_dir = self.build_dir / 'dists' / expected_dist_name
        if expected_dist_dir.exists():
            return expected_dist_dir
        old_dist_dir = self.build_dir / 'dists' / self.dist_name
        if old_dist_dir.exists():
            return old_dist_dir
        return expected_dist_dir

    def _get_release_mode(self):
        return 'release' if self._check_p4a_sign_env(False) else 'release-unsigned'

    @staticmethod
    def _check_p4a_sign_env(error):
        keys = ["KEYALIAS", "KEYSTORE_PASSWD", "KEYSTORE", "KEYALIAS_PASSWD"]
        check = True
        for key in keys:
            key = "P4A_RELEASE_{}".format(key)
            if key not in os.environ:
                if error:
                    log.error("Asking for release but %s is missing--sign will not be passed", key)
                check = False
        return check

    def _generate_whitelist(self, dist_dir):
        with (dist_dir / 'whitelist.txt').open('w') as f:
            for entry in self.p4a_whitelist:
                print(entry, file = f)

    def _permissions(self):
        for permission in self.permissions:
            words = permission.split('.')
            words[-1] = words[-1].upper()
            yield '.'.join(words)

    def _orientation(self):
        return 'sensor' if self.orientation == 'all' else self.orientation

    def build_package(self):
        dist_dir = self._get_dist_dir()
        version = self.config.get_version()
        self._update_libraries_references(dist_dir)
        self._generate_whitelist(dist_dir)
        def downstreamargs():
            yield 'name', self.config.get('app', 'title')
            yield 'version', version
            yield 'package', self.fqpackage
            yield 'min_sdk_version', int(self.config.getdefault('app', 'android.minapi', self.android_minapi))
            yield 'android_entrypoint', self.config.getdefault('app', 'android.entrypoint', 'org.kivy.android.PythonActivity')
            yield 'android_apptheme', self.config.getdefault('app', 'android.apptheme', '@android:style/Theme.NoTitleBar')
            yield 'permissions', list(self._permissions())
            yield 'compile_options', self.config.getlist('app', 'android.add_compile_options', [])
            yield 'gradle_repositories', self.config.getlist('app','android.add_gradle_repositories', [])
            yield 'packaging_options', self.config.getlist('app','android.add_packaging_options', [])
            yield 'meta_data', ['='.join(korv.strip() for korv in item) for item in self.meta_data.items()]
            yield 'add_activity', self.config.getlist('app', 'android.add_activities', [])
            icon = self.config.getdefault('app', 'icon.filename', '')
            yield 'icon', (self.workspace / icon).expanduser().resolve() if icon else None
            yield 'wakelock', True if self.config.getbooldefault('app', 'android.wakelock', False) else None
            intent_filters = self.config.getdefault('app', 'android.manifest.intent_filters', '')
            yield 'intent_filters', self.workspace / intent_filters if intent_filters else None
            launch_mode = self.config.getdefault('app', 'android.manifest.launch_mode', '')
            yield 'activity_launch_mode', launch_mode if launch_mode else 'singleTask'
            if self.bootstrapname != 'service_only':
                yield 'orientation', self._orientation()
                yield 'window', not self.config.getbooldefault('app', 'fullscreen', True)
                presplash = self.config.getdefault('app', 'presplash.filename', '')
                yield 'presplash', (self.workspace / presplash).expanduser().resolve() if presplash else None
                presplash_color = self.config.getdefault('app', 'android.presplash_color', None)
                yield 'presplash_color', presplash_color if presplash_color else '#000000'
            yield 'sign', True if self.build_mode != 'debug' and self._check_p4a_sign_env(True) else None
            yield 'services', self.config.getlist('app', 'services', [])
            yield 'android_used_libs', self.config.getlist('app', 'android.uses_library', [])
            depends = self.config.getlist('app', 'android.gradle_dependencies', [])
            yield 'depends', depends if depends else None
            if self.bootstrapname == 'webview':
                yield 'port', '5000'
        makeapk(
            self.dirs.android_sdk_dir,
            self.dirs.android_ndk_dir,
            self.android_api,
            self.dist_name,
            self.bootstrapname,
            self.arch,
            self.build_dir,
            self.ndk_api,
            self.workspace / 'local_recipes',
            self.dirs.app_dir,
            self.build_mode != 'debug',
            SimpleNamespace(**dict(downstreamargs())),
        )
        if self.build_mode == 'debug':
            mode_sign = mode = 'debug'
        else:
            mode_sign = "release"
            mode = self._get_release_mode()
        apk = f'{dist_dir.name}-{mode}.apk'
        apk_dir = dist_dir / "build" / "outputs" / "apk" / mode_sign
        apk_dest = f"{self.dist_name}-{version}-{self.config['app']['commit']}-{self.arch}-{mode}.apk"
        shutil.copyfile(apk_dir / apk, self.dirs.bin_dir / apk_dest)
        log.info('Android packaging done!')
        log.info("APK %s available in the bin directory", apk_dest)
        self.state['android:latestapk'] = apk_dest
        self.state['android:latestmode'] = self.build_mode

    def _update_libraries_references(self, dist_dir):
        project_fn = dist_dir / 'project.properties'
        if not project_fn.exists():
            content = ['target=android-{}\n'.format(self.android_api), f"APP_PLATFORM={self.android_minapi}\n"]
        else:
            with project_fn.open(encoding = 'utf-8') as fd:
                content = fd.readlines()
        references = []
        for line in content[:]:
            if not line.startswith('android.library.reference.'):
                continue
            content.remove(line)
        with project_fn.open('w', encoding = 'utf-8') as fd:
            try:
                fd.writelines((line.decode('utf-8') for line in content))
            except:
                fd.writelines(content)
            if content and not content[-1].endswith(u'\n'):
                fd.write(u'\n')
            for index, ref in enumerate(references):
                fd.write(u'android.library.reference.{}={}\n'.format(index + 1, ref))
        log.debug('project.properties updated')
