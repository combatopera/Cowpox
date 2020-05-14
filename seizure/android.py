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

from .libs.version import parse
from distutils.version import LooseVersion
from glob import glob
from lagoon import tar, unzip
from os.path import exists, join, realpath, expanduser, basename, relpath
from pathlib import Path
from pipes import quote
from pythonforandroid.distribution import generate_dist_folder_name
from pythonforandroid.mirror import download
from pythonforandroid.recommendations import RECOMMENDED_NDK_VERSION
from shutil import copyfile
import logging, os, shutil, sys

log = logging.getLogger(__name__)
ANDROID_API = '27'
ANDROID_MINAPI = '21'
APACHE_ANT_VERSION = '1.9.4'
# Default SDK tag to download. This is not a configurable option
# because it doesn't seem to matter much, it is normally correct to
# download once then update all the components as buildozer already
# does.
DEFAULT_SDK_TAG = '4333796'
DEFAULT_ARCH = 'armeabi-v7a'
USE_COLOR = 'NO_COLOR' not in os.environ

def _file_matches(patterns):
    result = []
    for pattern in patterns:
        matches = glob(expanduser(pattern.strip()))
        result.extend(matches)
    return result

def _file_copytree(src, dest):
    print('copy {} to {}'.format(src, dest))
    if os.path.isdir(src):
        if not os.path.isdir(dest):
            os.makedirs(dest)
        files = os.listdir(src)
        for f in files:
            _file_copytree(Path(src, f), Path(dest, f))
    else:
        copyfile(src, dest)

def _file_extract(archive, cwd):
    if archive.endswith('.tar.gz'):
        tar.xzf.print(archive, cwd = cwd)
    elif archive.endswith('.zip'):
        unzip._q.print(archive, cwd = cwd)
    else:
        raise Exception(f"Unhandled extraction for type {archive}")

def _file_rename(source, target, cwd):
    if cwd:
        source = Path(cwd, source)
        target = Path(cwd, target)
    log.debug('Rename %s to %s', source, target)
    if not target.parent.is_dir():
        log.error('Rename %s to %s fails because %s is not a directory', source, target, target)
    shutil.move(source, target)

class TargetAndroid:

    p4a_apk_cmd = "apk --debug --bootstrap="
    p4a_recommended_ndk_version = None
    javac_cmd = 'javac'
    keytool_cmd = 'keytool'

    def __init__(self, config, state, buildozer, build_mode):
        self.android_ndk_version = config.getdefault('app', 'android.ndk', RECOMMENDED_NDK_VERSION)
        self.android_api = config.getdefault('app', 'android.api', ANDROID_API)
        self.android_minapi = config.getdefault('app', 'android.minapi', ANDROID_MINAPI)
        self.android_sdk_dir = buildozer.global_platform_dir / 'android-sdk'
        self.android_ndk_dir = buildozer.global_platform_dir / f"android-ndk-r{config.getdefault('app', 'android.ndk', self.android_ndk_version)}"
        self.apache_ant_dir = buildozer.global_platform_dir / f"apache-ant-{config.getdefault('app', 'android.ant', APACHE_ANT_VERSION)}"
        self.sdkmanager_path = self.android_sdk_dir / 'tools' / 'bin' / 'sdkmanager'
        self.config = config
        self.state = state
        self.buildozer = buildozer
        self._arch = config.getdefault('app', 'android.arch', DEFAULT_ARCH)
        self._build_dir = buildozer.platform_dir / f"build-{self._arch}"
        self._p4a_cmd = '{} -m pythonforandroid.toolchain '.format(sys.executable)
        self._p4a_bootstrap = config.getdefault('app', 'p4a.bootstrap', 'sdl2')
        self.p4a_apk_cmd += self._p4a_bootstrap
        color = 'always' if USE_COLOR else 'never'
        self.extra_p4a_args = ' --color={} --storage-dir="{}"'.format(color, self._build_dir)
        # minapi should match ndk-api, so can use the same default if
        # nothing is specified
        ndk_api = config.getdefault('app', 'android.ndk_api', self.android_minapi)
        self.extra_p4a_args += ' --ndk-api={}'.format(ndk_api)
        hook = config.getdefault("app", "p4a.hook", None)
        if hook is not None:
            self.extra_p4a_args += ' --hook={}'.format(realpath(hook))
        port = config.getdefault('app', 'p4a.port', None)
        if port is not None:
            self.extra_p4a_args += ' --port={}'.format(port)
        self.build_mode = build_mode

    def _p4a(self, cmd, **kwargs):
        return self.buildozer.cmd(self._p4a_cmd + cmd + self.extra_p4a_args, **kwargs)

    def _sdkmanager(self, *args, **kwargs):
        kwargs['cwd'] = kwargs.get('cwd', self.android_sdk_dir)
        command = f"{self.sdkmanager_path} {' '.join(args)}"
        return_child = kwargs.pop('return_child', False)
        if return_child:
            return self.buildozer.cmd_expect(command, **kwargs)
        else:
            kwargs['get_stdout'] = kwargs.get('get_stdout', True)
            return self.buildozer.cmd(command, **kwargs)

    def check_requirements(self):
        self.adb_cmd = self.android_sdk_dir / 'platform-tools' / 'adb'
        # Check for C header <zlib.h>.
        _, _, returncode_dpkg = self.buildozer.cmd('dpkg --version', break_on_error = False)
        is_debian_like = (returncode_dpkg == 0)
        if is_debian_like and not Path('/usr/include/zlib.h').exists():
            raise Exception('zlib headers must be installed, run: sudo apt-get install zlib1g-dev')
        # Need to add internally installed ant to path for external tools
        # like adb to use
        path = [str(self.apache_ant_dir / 'bin')]
        if 'PATH' in self.buildozer.environ:
            path.append(self.buildozer.environ['PATH'])
        else:
            path.append(os.environ['PATH'])
        self.buildozer.environ['PATH'] = os.pathsep.join(path)

    def _install_apache_ant(self):
        ant_dir = self.apache_ant_dir
        if Path(ant_dir).exists():
            log.info('Apache ANT found at %s', ant_dir)
            return ant_dir

        if not os.path.exists(ant_dir):
            os.makedirs(ant_dir)
        log.info('Android ANT is missing, downloading')
        archive = f"apache-ant-{APACHE_ANT_VERSION}-bin.tar.gz"
        url = 'http://archive.apache.org/dist/ant/binaries/'
        download(url, archive, ant_dir)
        _file_extract(archive, ant_dir)
        log.info('Apache ANT installation done.')
        return ant_dir

    def _install_android_sdk(self):
        sdk_dir = self.android_sdk_dir
        if sdk_dir.exists():
            log.info('Android SDK found at %s', sdk_dir)
            return sdk_dir
        log.info('Android SDK is missing, downloading')
        archive = f"sdk-tools-linux-{DEFAULT_SDK_TAG}.zip"
        if not os.path.exists(sdk_dir):
            os.makedirs(sdk_dir)

        url = 'http://dl.google.com/android/repository/'
        download(url, archive, sdk_dir)
        log.info('Unpacking Android SDK')
        _file_extract(archive, sdk_dir)
        log.info('Android SDK tools base installation done.')
        return sdk_dir

    def _install_android_ndk(self):
        ndk_dir = self.android_ndk_dir
        if Path(ndk_dir).exists():
            log.info('Android NDK found at %s', ndk_dir)
            return ndk_dir
        log.info('Android NDK is missing, downloading')
        archive = f"android-ndk-r{self.android_ndk_version}-linux-x86_64.zip"
        unpacked = f"android-ndk-r{self.android_ndk_version}"
        url = 'https://dl.google.com/android/repository/'
        download(url, archive, self.buildozer.global_platform_dir)
        log.info('Unpacking Android NDK')
        _file_extract(archive, self.buildozer.global_platform_dir)
        _file_rename(unpacked, ndk_dir, cwd = self.buildozer.global_platform_dir)
        log.info('Android NDK installation done.')
        return ndk_dir

    def _android_list_build_tools_versions(self):
        available_packages = self._sdkmanager('--list')

        lines = available_packages[0].split('\n')

        build_tools_versions = []

        for line in lines:
            if not line.strip().startswith('build-tools;'):
                continue
            package_name = line.strip().split(' ')[0]
            assert package_name.count(';') == 1, (
                'could not parse package "{}"'.format(package_name))
            version = package_name.split(';')[1]

            build_tools_versions.append(parse(version))

        return build_tools_versions

    def _android_get_installed_platform_tools_version(self):
        platform_tools_dir = self.android_sdk_dir / 'platform-tools'
        if not platform_tools_dir.exists():
            return None
        data_file = platform_tools_dir / 'source.properties'
        if not data_file.exists():
            return None
        with data_file.open() as fileh:
            lines = fileh.readlines()
        for line in lines:
            if line.startswith('Pkg.Revision='):
                return line.split('=')[1].strip()
        log.error('Read %s but found no Pkg.Revision', data_file)
        # Don't actually exit, in case the build env is
        # okay. Something else will fault if it's important.

    def _android_update_sdk(self, *sdkmanager_commands):
        """Update the tools and package-tools if possible"""
        auto_accept_license = self.config.getbooldefault(
            'app', 'android.accept_sdk_license', False)

        kwargs = {}
        if auto_accept_license:
            # `SIGPIPE` is not being reported somehow, but `EPIPE` is.
            # This leads to a stderr "Broken pipe" message which is harmless,
            # but doesn't look good on terminal, hence redirecting to /dev/null
            yes_command = 'yes 2>/dev/null'
            command = '{} | {} --licenses'.format(
                yes_command, self.sdkmanager_path)
            self.buildozer.cmd(command, cwd=self.android_sdk_dir)
        else:
            kwargs['show_output'] = True

        self._sdkmanager(*sdkmanager_commands, **kwargs)

    def _read_version_subdir(self, *args):
        versions = []
        if not os.path.exists(join(*args)):
            log.debug("build-tools folder not found %s", join(*args))
            return parse("0")
        for v in os.listdir(join(*args)):
            try:
                versions.append(parse(v))
            except:
                pass
        if not versions:
            log.error('Unable to find the latest version for %s', join(*args))
            return parse("0")
        return max(versions)

    def _find_latest_package(self, packages, key):
        package_versions = []
        for p in packages:
            if not p.startswith(key):
                continue
            version_string = p.split(key)[-1]
            version = parse(version_string)
            package_versions.append(version)
        if not package_versions:
            return
        return max(package_versions)

    def _install_android_packages(self):

        # if any of theses value change into the buildozer.spec, retry the
        # update
        cache_key = 'android:sdk_installation'
        cache_value = [
            self.android_api, self.android_minapi, self.android_ndk_version,
            str(self.android_sdk_dir), str(self.android_ndk_dir)
        ]
        if self.state.get(cache_key, None) == cache_value:
            return True

        # 1. update the tool and platform-tools if needed

        skip_upd = self.config.getbooldefault(
            'app', 'android.skip_update', False)

        if not skip_upd:
            log.info('Installing/updating SDK platform tools if necessary')
            # just calling sdkmanager with the items will install them if necessary
            self._android_update_sdk('tools', 'platform-tools')
            self._android_update_sdk('--update')
        else:
            log.info('Skipping Android SDK update due to spec file setting')
            log.info('Note: this also prevents installing missing SDK components')
        # 2. install the latest build tool
        log.info('Updating SDK build tools if necessary')
        installed_v_build_tools = self._read_version_subdir(self.android_sdk_dir,
                                                  'build-tools')
        available_v_build_tools = self._android_list_build_tools_versions()
        if not available_v_build_tools:
            log.error('Did not find any build tools available to download')
        latest_v_build_tools = sorted(available_v_build_tools)[-1]
        if latest_v_build_tools > installed_v_build_tools:
            if not skip_upd:
                self._android_update_sdk(
                    '"build-tools;{}"'.format(latest_v_build_tools))
                installed_v_build_tools = latest_v_build_tools
            else:
                log.info('Skipping update to build tools %s due to spec setting', latest_v_build_tools)
        # 3. finally, install the android for the current api
        log.info('Downloading platform api target if necessary')
        android_platform = self.android_sdk_dir / 'platforms' / f"android-{self.android_api}"
        if not android_platform.exists():
            if not skip_upd:
                self._sdkmanager('"platforms;android-{}"'.format(self.android_api))
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
        self.buildozer.environ.update({
            'PACKAGES_PATH': self.buildozer.global_buildozer_dir / self.buildozer.targetname / 'packages',
            'ANDROIDSDK': self.android_sdk_dir,
            'ANDROIDNDK': self.android_ndk_dir,
            'ANDROIDAPI': self.android_api,
            'ANDROIDMINAPI': self.android_minapi,
        })

    def compile_platform(self):
        app_requirements = self.config.getlist(
            'app', 'requirements', '')
        dist_name = self.config.get('app', 'package.name')
        local_recipes = self.get_local_recipes_dir()
        requirements = ','.join(app_requirements)
        options = []

        source_dirs = {
            'P4A_{}_DIR'.format(name[20:]): realpath(expanduser(value))
            for name, value in self.config.items('app')
            if name.startswith('requirements.source.')
            }
        if source_dirs:
            self.buildozer.environ.update(source_dirs)
            log.info('Using custom source dirs:\n    %s', '\n    '.join(f'{k} = {v}' for k, v in source_dirs.items()))
        if self.config.getbooldefault('app', 'android.copy_libs', True):
            options.append("--copy-libs")
        # support for recipes in a local directory within the project
        if local_recipes:
            options.append('--local-recipes')
            options.append(local_recipes)
        self._p4a(
            ("create --dist_name={} --bootstrap={} --requirements={} "
             "--arch {} {}").format(
                 dist_name, self._p4a_bootstrap, requirements,
                 self._arch, " ".join(options)),
            get_stdout=True)[0]

    def get_dist_dir(self, dist_name, arch):
        """Find the dist dir with the given name and target arch, if one
        already exists, otherwise return a new dist_dir name.
        """
        expected_dist_name = generate_dist_folder_name(dist_name, arch_names=[arch])

        # If the expected dist name does exist, simply use that
        expected_dist_dir = self._build_dir / 'dists' / expected_dist_name
        if expected_dist_dir.exists():
            return expected_dist_dir
        # For backwards compatibility, check if a directory without
        # the arch exists. If so, this is probably the target dist.
        old_dist_dir = self._build_dir / 'dists' / dist_name
        if old_dist_dir.exists():
            return old_dist_dir
        # If no directory has been found yet, our dist probably
        # doesn't exist yet, so use the expected name
        return expected_dist_dir

    def get_local_recipes_dir(self):
        local_recipes = self.config.getdefault('app', 'p4a.local_recipes')
        return realpath(expanduser(local_recipes)) if local_recipes else None

    def execute_build_package(self, build_cmd):
        # wrapper from previous old_toolchain to new toolchain
        dist_name = self.config.get('app', 'package.name')
        local_recipes = self.get_local_recipes_dir()
        cmd = [self.p4a_apk_cmd, "--dist_name", dist_name]
        for args in build_cmd:
            option, values = args[0], args[1:]
            if option == "debug":
                continue
            elif option == "release":
                cmd.append("--release")
                if self.check_p4a_sign_env(True):
                    cmd.append("--sign")
                continue
            if option == "--window":
                cmd.append("--window")
            elif option == "--sdk":
                cmd.append("--android_api")
                cmd.extend(values)
            else:
                cmd.extend(args)

        # support for presplash background color
        presplash_color = self.config.getdefault('app', 'android.presplash_color', None)
        if presplash_color:
            cmd.append('--presplash-color')
            cmd.append("'{}'".format(presplash_color))

        # support for services
        services = self.config.getlist('app', 'services', [])
        for service in services:
            cmd.append("--service")
            cmd.append(service)

        # support for copy-libs
        if self.config.getbooldefault('app', 'android.copy_libs', True):
            cmd.append("--copy-libs")

        # support for recipes in a local directory within the project
        if local_recipes:
            cmd.append('--local-recipes')
            cmd.append(local_recipes)

        # support for blacklist/whitelist filename
        whitelist_src = self.config.getdefault('app', 'android.whitelist_src', None)
        blacklist_src = self.config.getdefault('app', 'android.blacklist_src', None)
        if whitelist_src:
            cmd.append('--whitelist')
            cmd.append(realpath(whitelist_src))
        if blacklist_src:
            cmd.append('--blacklist')
            cmd.append(realpath(blacklist_src))

        # support for aars
        aars = self.config.getlist('app', 'android.add_aars', [])
        for aar in aars:
            cmd.append('--add-aar')
            cmd.append(realpath(aar))

        # support for uses-lib
        uses_library = self.config.getlist(
            'app', 'android.uses_library', '')
        for lib in uses_library:
            cmd.append('--uses-library={}'.format(lib))

        # support for gradle dependencies
        gradle_dependencies = self.config.getlist('app', 'android.gradle_dependencies', [])
        for gradle_dependency in gradle_dependencies:
            cmd.append('--depend')
            cmd.append(gradle_dependency)

        cmd.append('--arch')
        cmd.append(self._arch)
        self._p4a(' '.join(map(str, cmd))) # FIXME: Use lagoon.

    def get_release_mode(self):
        if self.check_p4a_sign_env():
            return "release"
        return "release-unsigned"

    def check_p4a_sign_env(self, error=False):
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
        config = self.config
        package_domain = config.getdefault('app', 'package.domain', '')
        package = config.get('app', 'package.name')
        if package_domain:
            package = package_domain + '.' + package
        return package.lower()

    def _generate_whitelist(self, dist_dir):
        p4a_whitelist = self.config.getlist(
            'app', 'android.whitelist') or []
        whitelist_fn = join(dist_dir, 'whitelist.txt')
        with open(whitelist_fn, 'w') as fd:
            for wl in p4a_whitelist:
                fd.write(wl + '\n')

    def build_package(self):
        dist_name = self.config.get('app', 'package.name')
        arch = self.config.getdefault('app', 'android.arch', DEFAULT_ARCH)
        dist_dir = self.get_dist_dir(dist_name, arch)
        config = self.config
        package = self._get_package()
        version = self.config.get_version()
        # add extra libs/armeabi files in dist/default/libs/armeabi
        # (same for armeabi-v7a, arm64-v8a, x86, mips)
        for config_key, lib_dir in (
                ('android.add_libs_armeabi', 'armeabi'),
                ('android.add_libs_armeabi_v7a', 'armeabi-v7a'),
                ('android.add_libs_arm64_v8a', 'arm64-v8a'),
                ('android.add_libs_x86', 'x86'),
                ('android.add_libs_mips', 'mips')):

            patterns = config.getlist('app', config_key, [])
            if not patterns:
                continue
            if self._arch != lib_dir:
                continue
            log.debug("Search and copy libs for %s", lib_dir)
            for fn in _file_matches(patterns):
                self.buildozer.file_copy(
                    join(self.buildozer.root_dir, fn),
                    join(dist_dir, 'libs', lib_dir, basename(fn)))

        # update the project.properties libraries references
        self._update_libraries_references(dist_dir)

        # add src files
        self._add_java_src(dist_dir)

        # generate the whitelist if needed
        self._generate_whitelist(dist_dir)

        # build the app
        build_cmd = [
            ("--name", quote(config.get('app', 'title'))),
            ("--version", version),
            ("--package", package),
            ("--minsdk", config.getdefault('app', 'android.minapi',
                                           self.android_minapi)),
            ("--ndk-api", config.getdefault('app', 'android.minapi',
                                            self.android_minapi)),
        ]
        is_private_storage = config.getbooldefault(
            'app', 'android.private_storage', True)
        if is_private_storage:
            build_cmd += [("--private", self.buildozer.app_dir)]
        else:
            build_cmd += [("--dir", self.buildozer.app_dir)]

        # add permissions
        permissions = config.getlist('app', 'android.permissions', [])
        for permission in permissions:
            # force the latest component to be uppercase
            permission = permission.split('.')
            permission[-1] = permission[-1].upper()
            permission = '.'.join(permission)
            build_cmd += [("--permission", permission)]

        # android.entrypoint
        entrypoint = config.getdefault('app', 'android.entrypoint', 'org.kivy.android.PythonActivity')
        build_cmd += [('--android-entrypoint', entrypoint)]

        # android.apptheme
        apptheme = config.getdefault('app', 'android.apptheme', '@android:style/Theme.NoTitleBar')
        build_cmd += [('--android-apptheme', apptheme)]

        # android.compile_options
        compile_options = config.getlist('app', 'android.add_compile_options', [])
        for option in compile_options:
            build_cmd += [('--add-compile-option', option)]

        # android.add_gradle_repositories
        repos = config.getlist('app','android.add_gradle_repositories', [])
        for repo in repos:
            build_cmd += [('--add-gradle-repository', repo)]

        # android packaging options
        pkgoptions = config.getlist('app','android.add_packaging_options', [])
        for pkgoption in pkgoptions:
            build_cmd += [('--add-packaging-option', pkgoption)]

        # meta-data
        meta_datas = config.getlistvalues('app', 'android.meta_data', [])
        for meta in meta_datas:
            key, value = meta.split('=', 1)
            meta = '{}={}'.format(key.strip(), value.strip())
            build_cmd += [("--meta-data", meta)]

        # add extra Java jar files
        add_jars = config.getlist('app', 'android.add_jars', [])
        for pattern in add_jars:
            pattern = join(self.buildozer.root_dir, pattern)
            matches = glob(expanduser(pattern.strip()))
            if matches:
                for jar in matches:
                    build_cmd += [("--add-jar", jar)]
            else:
                raise SystemError('Failed to find jar file: {}'.format(
                    pattern))

        # add Java activity
        add_activities = config.getlist('app', 'android.add_activities', [])
        for activity in add_activities:
            build_cmd += [("--add-activity", activity)]

        # add presplash
        presplash = config.getdefault('app', 'presplash.filename', '')
        if presplash:
            build_cmd += [("--presplash", join(self.buildozer.root_dir,
                                               presplash))]

        # add icon
        icon = config.getdefault('app', 'icon.filename', '')
        if icon:
            build_cmd += [("--icon", join(self.buildozer.root_dir, icon))]

        # OUYA Console support
        ouya_category = config.getdefault('app', 'android.ouya.category',
                                          '').upper()
        if ouya_category:
            if ouya_category not in ('GAME', 'APP'):
                raise SystemError(
                    'Invalid android.ouya.category: "{}" must be one of GAME or APP'.format(
                        ouya_category))
            # add icon
            ouya_icon = config.getdefault('app', 'android.ouya.icon.filename',
                                          '')
            build_cmd += [("--ouya-category", ouya_category)]
            build_cmd += [("--ouya-icon", join(self.buildozer.root_dir,
                                               ouya_icon))]

        if config.getdefault('app','p4a.bootstrap','sdl2') != 'service_only':
            # add orientation
            orientation = config.getdefault('app', 'orientation', 'landscape')
            if orientation == 'all':
                orientation = 'sensor'
            build_cmd += [("--orientation", orientation)]

            # fullscreen ?
            fullscreen = config.getbooldefault('app', 'fullscreen', True)
            if not fullscreen:
                build_cmd += [("--window", )]

        # wakelock ?
        wakelock = config.getbooldefault('app', 'android.wakelock', False)
        if wakelock:
            build_cmd += [("--wakelock", )]

        # intent filters
        intent_filters = config.getdefault(
            'app', 'android.manifest.intent_filters', '')
        if intent_filters:
            build_cmd += [("--intent-filters", join(self.buildozer.root_dir,
                                                    intent_filters))]

        # activity launch mode
        launch_mode = config.getdefault(
            'app', 'android.manifest.launch_mode', '')
        if launch_mode:
            build_cmd += [("--activity-launch-mode", launch_mode)]

        # build only in debug right now.
        if self.build_mode == 'debug':
            build_cmd += [("debug", )]
            mode = 'debug'
            mode_sign = mode
        else:
            build_cmd += [("release", )]
            mode_sign = "release"
            mode = self.get_release_mode()

        self.execute_build_package(build_cmd)
        build_tools_versions = os.listdir(join(self.android_sdk_dir, "build-tools"))
        build_tools_versions = sorted(build_tools_versions, key=LooseVersion)
        build_tools_version = build_tools_versions[-1]
        gradle_files = ["build.gradle", "gradle", "gradlew"]
        is_gradle_build = build_tools_version >= "25.0" and any(
            (exists(join(dist_dir, x)) for x in gradle_files))
        packagename = config.get('app', 'package.name')

        if is_gradle_build:
            # on gradle build, the apk use the package name, and have no version
            packagename_src = basename(dist_dir)  # gradle specifically uses the folder name
            apk = u'{packagename}-{mode}.apk'.format(
                packagename=packagename_src, mode=mode)
            apk_dir = join(dist_dir, "build", "outputs", "apk", mode_sign)
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
            apk_dir = join(dist_dir, "bin")
        apk_dest = f"{packagename}-{version}-{self.config['app']['commit']}-{self._arch}-{mode}.apk"
        copyfile(join(apk_dir, apk), self.buildozer.bin_dir / apk_dest)
        log.info('Android packaging done!')
        log.info("APK %s available in the bin directory", apk_dest)
        self.state['android:latestapk'] = apk_dest
        self.state['android:latestmode'] = self.build_mode

    def _update_libraries_references(self, dist_dir):
        # ensure the project.properties exist
        project_fn = join(dist_dir, 'project.properties')
        if not Path(project_fn).exists():
            content = [
                'target=android-{}\n'.format(self.android_api),
                'APP_PLATFORM={}\n'.format(self.android_minapi)]
        else:
            with open(project_fn, encoding = 'utf-8') as fd:
                content = fd.readlines()

        # extract library reference
        references = []
        for line in content[:]:
            if not line.startswith('android.library.reference.'):
                continue
            content.remove(line)

        # convert our references to relative path
        app_references = self.config.getlist(
            'app', 'android.library_references', [])
        source_dir = realpath(self.config.getdefault(
            'app', 'source.dir', '.'))
        for cref in app_references:
            # get the full path of the current reference
            ref = realpath(join(source_dir, cref))
            if not Path(ref).exists():
                log.error('Invalid library reference (path not found): %s', cref)
                exit(1)
            # get a relative path from the project file
            ref = relpath(ref, realpath(dist_dir))
            # ensure the reference exists
            references.append(ref)

        # recreate the project.properties
        with open(project_fn, 'w', encoding = 'utf-8') as fd:
            try:
                fd.writelines((line.decode('utf-8') for line in content))
            except:
                fd.writelines(content)
            if content and not content[-1].endswith(u'\n'):
                fd.write(u'\n')
            for index, ref in enumerate(references):
                fd.write(u'android.library.reference.{}={}\n'.format(index + 1, ref))
        log.debug('project.properties updated')

    def _add_java_src(self, dist_dir):
        java_src = self.config.getlist('app', 'android.add_src', [])

        gradle_files = ["build.gradle", "gradle", "gradlew"]
        is_gradle_build = any((
            exists(join(dist_dir, x)) for x in gradle_files))
        if is_gradle_build:
            src_dir = join(dist_dir, "src", "main", "java")
            log.info("Gradle project detected, copy files %s", src_dir)
        else:
            src_dir = join(dist_dir, 'src')
            log.info("Ant project detected, copy files in %s", src_dir)
        for pattern in java_src:
            for fn in glob(expanduser(pattern.strip())):
                last_component = basename(fn)
                _file_copytree(fn, join(src_dir, last_component))
