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
from .dirs import APACHE_ANT_VERSION, Dirs
from .jsonstore import JsonStore
from .libs.version import parse
from diapyr import types
from distutils.version import LooseVersion
from lagoon import tar, unzip, yes
from lagoon.program import Program
from pythonforandroid.distribution import generate_dist_folder_name
from pythonforandroid.mirror import download
import logging, os, shutil, sys

log = logging.getLogger(__name__)

class TargetAndroid:

    @types(Config, JsonStore, Dirs)
    def __init__(self, config, state, dirs):
        self.android_api = config.getdefault('app', 'android.api', '27')
        self.android_minapi = config.getdefault('app', 'android.minapi', '21')
        self.sdkmanager = Program.text(dirs.android_sdk_dir / 'tools' / 'bin' / 'sdkmanager').partial(cwd = dirs.android_sdk_dir)
        self.arch = config.getdefault('app', 'android.arch', 'armeabi-v7a')
        self.build_dir = dirs.platform_dir / f"build-{self.arch}"
        self.p4a = Program.text(sys.executable).partial('-m', 'pythonforandroid.toolchain', env = dict(
            ANDROIDSDK = dirs.android_sdk_dir,
            ANDROIDNDK = dirs.android_ndk_dir,
            ANDROIDAPI = self.android_api,
        ))
        self._p4a_bootstrap = config.getdefault('app', 'p4a.bootstrap', 'sdl2')
        self.p4a_apk_cmd = 'apk', '--debug', f"--bootstrap={self._p4a_bootstrap}"
        self.extra_p4a_args = '--color=always', f"--storage-dir={self.build_dir}", f"--ndk-api={config.getdefault('app', 'android.ndk_api', self.android_minapi)}"
        self.local_recipes = config.workspace / 'local_recipes'
        self.dist_name = config.get('app', 'package.name')
        self.config = config
        self.state = state
        self.dirs = dirs

    def _p4a(self, *args):
        self.p4a.print(*args, *self.extra_p4a_args)

    def _install_apache_ant(self):
        ant_dir = self.dirs.apache_ant_dir
        if ant_dir.exists():
            log.info('Apache ANT found at %s', ant_dir)
            return
        ant_dir.mkdir(parents = True)
        log.info('Android ANT is missing, downloading')
        archive = f"apache-ant-{APACHE_ANT_VERSION}-bin.tar.gz"
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
        archive = f"android-ndk-r{self.config.android_ndk_version}-linux-x86_64.zip"
        download('https://dl.google.com/android/repository/', archive, self.dirs.global_platform_dir)
        log.info('Unpacking Android NDK')
        unzip._q.print(archive, cwd = self.dirs.global_platform_dir)
        source = self.dirs.global_platform_dir / f"android-ndk-r{self.config.android_ndk_version}"
        log.debug('Rename %s to %s', source, ndk_dir)
        shutil.move(source, ndk_dir)
        log.info('Android NDK installation done.')

    def _android_list_build_tools_versions(self):
        lines = self.sdkmanager.__list().split('\n')
        build_tools_versions = []
        for line in lines:
            if not line.strip().startswith('build-tools;'):
                continue
            package_name = line.strip().split(' ')[0]
            assert package_name.count(';') == 1, f'could not parse package "{package_name}"'
            version = package_name.split(';')[1]
            build_tools_versions.append(parse(version))
        return build_tools_versions

    def _android_update_sdk(self, *args):
        if self.config.getbooldefault('app', 'android.accept_sdk_license', False):
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
            self.android_api, self.android_minapi, self.config.android_ndk_version,
            str(self.dirs.android_sdk_dir), str(self.dirs.android_ndk_dir),
        ]
        if self.state.get(cache_key, None) == cache_value:
            return
        skip_upd = self.config.getbooldefault('app', 'android.skip_update', False)
        if not skip_upd:
            log.info('Installing/updating SDK platform tools if necessary')
            self._android_update_sdk('tools', 'platform-tools')
            self._android_update_sdk('--update')
        else:
            log.info('Skipping Android SDK update due to spec file setting')
            log.info('Note: this also prevents installing missing SDK components')
        log.info('Updating SDK build tools if necessary')
        available_v_build_tools = self._android_list_build_tools_versions()
        if not available_v_build_tools:
            log.error('Did not find any build tools available to download')
        latest_v_build_tools = max(available_v_build_tools)
        if latest_v_build_tools > self._read_version_subdir(self.dirs.android_sdk_dir / 'build-tools'):
            if not skip_upd:
                self._android_update_sdk(f"build-tools;{latest_v_build_tools}")
            else:
                log.info('Skipping update to build tools %s due to spec setting', latest_v_build_tools)
        log.info('Downloading platform api target if necessary')
        if not (self.dirs.android_sdk_dir / 'platforms' / f"android-{self.android_api}").exists():
            if not skip_upd:
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
        app_requirements = self.config.getlist('app', 'requirements', '')
        requirements = ','.join(app_requirements)
        options = []
        if self.config.getbooldefault('app', 'android.copy_libs', True):
            options.append("--copy-libs")
        options.extend(['--local-recipes', self.local_recipes])
        self._p4a('create', f"--dist_name={self.dist_name}", f"--bootstrap={self._p4a_bootstrap}", f"--requirements={requirements}", '--arch', self.arch, *options)

    def _get_dist_dir(self):
        expected_dist_name = generate_dist_folder_name(self.dist_name, arch_names = [self.arch])
        expected_dist_dir = self.build_dir / 'dists' / expected_dist_name
        if expected_dist_dir.exists():
            return expected_dist_dir
        old_dist_dir = self.build_dir / 'dists' / self.dist_name
        if old_dist_dir.exists():
            return old_dist_dir
        return expected_dist_dir

    def _execute_build_package(self, build_cmd):
        cmd = []
        presplash_color = self.config.getdefault('app', 'android.presplash_color', None)
        if presplash_color:
            cmd += ['--presplash-color', f"{presplash_color}"]
        services = self.config.getlist('app', 'services', [])
        for service in services:
            cmd += ["--service", service]
        if self.config.getbooldefault('app', 'android.copy_libs', True):
            cmd.append("--copy-libs")
        cmd += ['--local-recipes', self.local_recipes]
        uses_library = self.config.getlist('app', 'android.uses_library', '')
        for lib in uses_library:
            cmd.append(f'--uses-library={lib}')
        gradle_dependencies = self.config.getlist('app', 'android.gradle_dependencies', [])
        for gradle_dependency in gradle_dependencies:
            cmd += ['--depend', gradle_dependency]
        self._p4a(*self.p4a_apk_cmd, '--dist_name', self.dist_name, *build_cmd, *cmd, '--arch', self.arch)

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

    def _get_package(self):
        package_domain = self.config.getdefault('app', 'package.domain', '')
        package = self.dist_name
        if package_domain:
            package = package_domain + '.' + package
        return package.lower()

    def _generate_whitelist(self, dist_dir):
        p4a_whitelist = self.config.getlist('app', 'android.whitelist') or []
        with (dist_dir / 'whitelist.txt').open('w') as fd:
            for wl in p4a_whitelist:
                fd.write(wl + '\n')

    def build_package(self):
        dist_dir = self._get_dist_dir()
        config = self.config
        version = self.config.get_version()
        self._update_libraries_references(dist_dir)
        self._generate_whitelist(dist_dir)
        build_cmd = [
            "--name", config.get('app', 'title'),
            "--version", version,
            "--package", self._get_package(),
            "--minsdk", config.getdefault('app', 'android.minapi', self.android_minapi),
            "--ndk-api", config.getdefault('app', 'android.minapi', self.android_minapi),
        ]
        is_private_storage = config.getbooldefault('app', 'android.private_storage', True)
        if is_private_storage:
            build_cmd += ["--private", self.dirs.app_dir]
        else:
            build_cmd += ["--dir", self.dirs.app_dir]
        permissions = config.getlist('app', 'android.permissions', [])
        for permission in permissions:
            permission = permission.split('.')
            permission[-1] = permission[-1].upper()
            permission = '.'.join(permission)
            build_cmd += ["--permission", permission]
        entrypoint = config.getdefault('app', 'android.entrypoint', 'org.kivy.android.PythonActivity')
        build_cmd += ['--android-entrypoint', entrypoint]
        apptheme = config.getdefault('app', 'android.apptheme', '@android:style/Theme.NoTitleBar')
        build_cmd += ['--android-apptheme', apptheme]
        compile_options = config.getlist('app', 'android.add_compile_options', [])
        for option in compile_options:
            build_cmd += ['--add-compile-option', option]
        repos = config.getlist('app','android.add_gradle_repositories', [])
        for repo in repos:
            build_cmd += ['--add-gradle-repository', repo]
        pkgoptions = config.getlist('app','android.add_packaging_options', [])
        for pkgoption in pkgoptions:
            build_cmd += ['--add-packaging-option', pkgoption]
        meta_datas = config.getlistvalues('app', 'android.meta_data', [])
        for meta in meta_datas:
            key, value = meta.split('=', 1)
            meta = '{}={}'.format(key.strip(), value.strip())
            build_cmd += ["--meta-data", meta]
        add_activities = config.getlist('app', 'android.add_activities', [])
        for activity in add_activities:
            build_cmd += ["--add-activity", activity]
        presplash = config.getdefault('app', 'presplash.filename', '')
        if presplash:
            build_cmd += ["--presplash", self.config.workspace / presplash]
        icon = config.getdefault('app', 'icon.filename', '')
        if icon:
            build_cmd += ["--icon", self.config.workspace / icon]
        ouya_category = config.getdefault('app', 'android.ouya.category', '').upper()
        if ouya_category:
            if ouya_category not in {'GAME', 'APP'}:
                raise SystemError(f'Invalid android.ouya.category: "{ouya_category}" must be one of GAME or APP')
            ouya_icon = config.getdefault('app', 'android.ouya.icon.filename', '')
            build_cmd += ["--ouya-category", ouya_category, "--ouya-icon", self.config.workspace / ouya_icon]
        if config.getdefault('app','p4a.bootstrap','sdl2') != 'service_only':
            orientation = config.getdefault('app', 'orientation', 'landscape')
            if orientation == 'all':
                orientation = 'sensor'
            build_cmd += ["--orientation", orientation]
            fullscreen = config.getbooldefault('app', 'fullscreen', True)
            if not fullscreen:
                build_cmd += ["--window"]
        wakelock = config.getbooldefault('app', 'android.wakelock', False)
        if wakelock:
            build_cmd += ["--wakelock"]
        intent_filters = config.getdefault('app', 'android.manifest.intent_filters', '')
        if intent_filters:
            build_cmd += ["--intent-filters", self.config.workspace / intent_filters]
        launch_mode = config.getdefault('app', 'android.manifest.launch_mode', '')
        if launch_mode:
            build_cmd += ["--activity-launch-mode", launch_mode]
        if self.config.build_mode == 'debug':
            mode = 'debug'
            mode_sign = mode
        else:
            build_cmd += ['--release']
            if self._check_p4a_sign_env(True):
                build_cmd += ['--sign']
            mode_sign = "release"
            mode = self._get_release_mode()
        self._execute_build_package(build_cmd)
        build_tools_versions = os.listdir(self.dirs.android_sdk_dir / "build-tools")
        build_tools_versions = sorted(build_tools_versions, key = LooseVersion)
        build_tools_version = build_tools_versions[-1]
        gradle_files = ["build.gradle", "gradle", "gradlew"]
        is_gradle_build = build_tools_version >= "25.0" and any((dist_dir / x).exists() for x in gradle_files)
        if is_gradle_build:
            apk = f'{dist_dir.name}-{mode}.apk'
            apk_dir = dist_dir / "build" / "outputs" / "apk" / mode_sign
        else:
            # on ant, the apk use the title, and have version
            bl = u'\'" ,'
            apptitle = config.get('app', 'title')
            if hasattr(apptitle, 'decode'):
                apptitle = apptitle.decode('utf-8')
            apktitle = ''.join([x for x in apptitle if x not in bl])
            apk = u'{title}-{version}-{mode}.apk'.format(
                title=apktitle,
                version=version,
                mode=mode)
            apk_dir = dist_dir / "bin"
        apk_dest = f"{self.dist_name}-{version}-{self.config['app']['commit']}-{self.arch}-{mode}.apk"
        shutil.copyfile(apk_dir / apk, self.dirs.bin_dir / apk_dest)
        log.info('Android packaging done!')
        log.info("APK %s available in the bin directory", apk_dest)
        self.state['android:latestapk'] = apk_dest
        self.state['android:latestmode'] = self.config.build_mode

    def _update_libraries_references(self, dist_dir):
        project_fn = dist_dir / 'project.properties'
        if not project_fn.exists():
            content = ['target=android-{}\n'.format(self.android_api), 'APP_PLATFORM={}\n'.format(self.android_minapi)]
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
