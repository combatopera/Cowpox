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
from .context import Context
from .dirs import Dirs
from .distribution import generate_dist_folder_name
from .libs.version import parse
from .mirror import Mirror
from .p4a import create, makeapk
from contextlib import contextmanager
from diapyr import types
from lagoon import unzip, yes
from lagoon.program import Program
from pathlib import Path
from types import SimpleNamespace
import logging, os, shutil

log = logging.getLogger(__name__)

@contextmanager
def okorclean(dirpath):
    okpath = dirpath / 'ok'
    if okpath.exists():
        yield True
        return
    dirpath.mkdirp()
    for child in dirpath.iterdir():
        shutil.rmtree(child)
    yield
    with okpath.open('w'):
        pass

Path.okorclean = okorclean

class TargetAndroid:

    @types(Config, Dirs, Mirror, Context)
    def __init__(self, config, dirs, mirror, context):
        self.android_ndk_version = config.android.ndk
        self.android_api = config.android.api
        self.android_minapi = config.android.minapi
        self.arch = config.android.arch
        self.dist_name = config.package.name
        self.bootstrapname = config.p4a.bootstrap
        self.acceptlicense = config.android.accept_sdk_license
        self.skip_upd = config.android.skip_update
        self.ndk_api = config.android.ndk_api
        self.requirements = config.requirements.list()
        self.fqpackage = config.package.fq
        self.build_mode = config.build_mode
        self.p4a_whitelist = config.android.whitelist.list()
        self.permissions = config.android.permissions.list()
        self.orientation = config.orientation
        self.meta_data = config.android.meta_data.dict()
        self.title = config.title
        self.android_entrypoint = config.android.entrypoint
        self.android_apptheme = config.android.apptheme
        self.version = config.version
        self.commit = config.commit
        self.compile_options = config.android.add_compile_options.list()
        self.gradle_repositories = config.android.add_gradle_repositories.list()
        self.packaging_options = config.android.add_packaging_options.list()
        self.add_activity = config.android.add_activities.list()
        self.wakelock = config.android.wakelock
        self.launch_mode = config.android.manifest.launch_mode
        self.fullscreen = config.fullscreen
        self.presplash_color = config.android.presplash_color
        self.services = config.services.list()
        self.android_used_libs = config.android.uses_library.list()
        self.depends = config.android.gradle_dependencies.list()
        self.projectdir = Path(config.container.src)
        self.icon = config.icon.filename
        self.intent_filters = config.android.manifest.intent_filters
        self.presplash = config.presplash.filename
        self.apkdir = Path(config.apk.dir)
        self.sdk_dir = Path(config.android_sdk_dir)
        self.ndk_dir = Path(config.android_ndk_dir)
        self.sdkmanager = Program.text(self.sdk_dir / 'tools' / 'bin' / 'sdkmanager').partial(cwd = self.sdk_dir)
        self.build_dir = dirs.platform_dir / f"build-{self.arch}"
        self.dirs = dirs
        self.mirror = mirror
        self.context = context

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
        if latest_v_build_tools > self._read_version_subdir(self.sdk_dir / 'build-tools'):
            if not self.skip_upd:
                self._android_update_sdk(f"build-tools;{latest_v_build_tools}")
            else:
                log.info('Skipping update to build tools %s due to spec setting', latest_v_build_tools)
        log.info('Downloading platform api target if necessary')
        if not (self.sdk_dir / 'platforms' / f"android-{self.android_api}").exists():
            if not self.skip_upd:
                self.sdkmanager.print(f"platforms;android-{self.android_api}")
            else:
                log.info('Skipping install API %s platform tools due to spec setting', self.android_api)
        log.info('Android packages installation done.')

    def install_platform(self):
        self._install_android_sdk()
        self._install_android_ndk()
        self._install_android_packages()

    def compile_platform(self):
        self.context.init()
        return create(
            self.context,
            self.dist_name,
            self.bootstrapname,
            self.arch,
            self.ndk_api,
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

    def build_package(self, dist):
        dist_dir = self._get_dist_dir()
        self._update_libraries_references(dist_dir)
        self._generate_whitelist(dist_dir)
        def downstreamargs():
            yield 'name', self.title
            yield 'version', self.version
            yield 'package', self.fqpackage
            yield 'min_sdk_version', self.android_minapi
            yield 'android_entrypoint', self.android_entrypoint
            yield 'android_apptheme', self.android_apptheme
            yield 'permissions', list(self._permissions())
            yield 'compile_options', self.compile_options
            yield 'gradle_repositories', self.gradle_repositories
            yield 'packaging_options', self.packaging_options
            yield 'meta_data', ['='.join(korv.strip() for korv in item) for item in self.meta_data.items()]
            yield 'add_activity', self.add_activity
            yield 'icon', None if self.icon is None else self.projectdir / self.icon
            yield 'wakelock', True if self.wakelock else None
            yield 'intent_filters', None if self.intent_filters is None else self.projectdir / self.intent_filters
            yield 'activity_launch_mode', self.launch_mode
            if self.bootstrapname != 'service_only':
                yield 'orientation', self._orientation()
                yield 'window', not self.fullscreen
                yield 'presplash', None if self.presplash is None else self.projectdir / self.presplash
                yield 'presplash_color', self.presplash_color
            yield 'sign', True if self.build_mode != 'debug' and self._check_p4a_sign_env(True) else None
            yield 'services', self.services
            yield 'android_used_libs', self.android_used_libs
            yield 'depends', self.depends if self.depends else None
            if self.bootstrapname == 'webview':
                yield 'port', '5000'
        makeapk(
            self.context,
            dist,
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
        apkpath = self.apkdir / f"{self.dist_name}-{self.version}-{self.commit}-{self.arch}-{mode}.apk"
        shutil.copyfile(apk_dir / apk, apkpath)
        log.info('Android packaging done!')
        return apkpath

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
