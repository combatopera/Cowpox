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

from . import AndroidProjectOK, APKPath, Arch, BundleOK, Graph, GraphInfo, skel
from .boot import Bootstrap
from .config import Config
from .container import compileall
from .make import Make
from .platform import Platform
from .util import enum
from aridity import Repl
from diapyr import types
from fnmatch import fnmatch
from jproperties import Properties
from lagoon import gradle
from pathlib import Path
from pkg_resources import resource_filename, resource_stream, resource_string
import logging, os, shutil, tarfile, time

log = logging.getLogger(__name__)

@enum(
    ['debug', 'assembleDebug'],
    ['release', 'assembleRelease'],
)
class Division:

    def __init__(self, name, goal):
        self.name = name
        self.goal = goal

@enum(
    ['debug', Division.debug, False],
    ['release-unsigned', Division.release, False],
    ['release', Division.release, True],
)
class BuildMode:

    def __init__(self, name, division, signing):
        self.name = name
        self.division = division
        self.signing = signing

@types(Config, this = BuildMode)
def getbuildmode(config):
    return getattr(BuildMode, config.build_mode)

class Assembly:

    @types(Config, BuildMode, AndroidProjectOK)
    def __init__(self, config, mode, _):
        self.android_project_dir = Path(config.android.project.dir)
        self.gradleenv = dict(ANDROID_HOME = config.SDK.dir, ANDROID_NDK_HOME = config.NDK.dir)
        self.gradlebuilddir = self.android_project_dir / 'build'
        self.mode = mode

    @types(Make, AndroidProjectOK, this = APKPath)
    def build_package(self, make, _):
        def target():
            yield self.gradlebuilddir
            gradle.__no_daemon.print(self.mode.division.goal, env = self.gradleenv, cwd = self.android_project_dir)
            log.info('Android packaging done!')
        make(target)
        return self.gradlebuilddir / 'outputs' / 'apk' / self.mode.division.name / f"{self.android_project_dir.name}-{self.mode.name}.apk"

class AssetArchive:

    @types(Config, GraphInfo, Graph)
    def __init__(self, config, graphinfo, graph):
        self.sourcedirs = [Path(d) for d in [config.private.dir, config.bootstrap.private.dir]] # FIXME LATER: The latter should incorporate common.
        self.tarpath = Path(config.android.project.assets.dir, 'private.mp3')
        self.WHITELIST_PATTERNS = ['pyconfig.h'] if config.bootstrap.name in {'sdl2', 'webview', 'service_only'} else []
        self.WHITELIST_PATTERNS.extend(config.android.whitelist.list())
        self.BLACKLIST_PATTERNS = [
            '^*.hg/*',
            '^*.git/*',
            '^*.bzr/*',
            '^*.svn/*',
            '~',
            '*.bak',
            '*.swp',
            '*.py',
        ] + resource_string(__name__, 'blacklist.txt').decode().splitlines()
        if config.bootstrap.name in {'webview', 'service_only'} or 'sqlite3' not in graphinfo.recipenames:
            self.BLACKLIST_PATTERNS += ['sqlite3/*', 'lib-dynload/_sqlite3.so']
        self.graph = graph

    def _accept(self, path):
        def match_filename(pattern_list):
            for pattern in pattern_list:
                if pattern.startswith('^'):
                    pattern = pattern[1:]
                else:
                    pattern = '*/' + pattern
                if fnmatch(path, pattern):
                    return True
        return match_filename(self.WHITELIST_PATTERNS) or not match_filename(self.BLACKLIST_PATTERNS)

    def makeprivate(self):
        if self.tarpath.exists():
            self.tarpath.unlink()
        def mkdirp(relpath):
            if relpath in tardirs:
                return
            mkdirp(relpath.parent)
            info = tarfile.TarInfo(str(relpath))
            info.type = tarfile.DIRTYPE
            info.mode |= 0o111
            tf.addfile(info)
            tardirs.add(relpath)
        with tarfile.open(self.tarpath.pmkdirp(), 'w:gz', format = tarfile.USTAR_FORMAT) as tf:
            tardirs = {Path('.')}
            for sd in self.sourcedirs:
                if sd.exists():
                    for path in self._listfiles(sd):
                        relpath = path.relative_to(sd)
                        mkdirp(relpath.parent)
                        tf.add(path, relpath)

    def _listfiles(self, dirpath):
        subdirs = []
        for path in dirpath.iterdir():
            if path.is_file():
                if self._accept(path):
                    yield path
            else:
                subdirs.append(path)
        for subdir in subdirs:
            yield from self._listfiles(subdir)

class AndroidProject:

    @types(Config, Arch, Platform, AssetArchive, BuildMode, Bootstrap)
    def __init__(self, config, arch, platform, assetarchive, mode, bootstrap):
        self.ndk_api = config.android.ndk_api
        self.min_sdk_version = config.android.minSdkVersion
        if self.ndk_api != self.min_sdk_version:
            log.warning("--minsdk argument does not match the api that is compiled against. Only proceed if you know what you are doing, otherwise use --minsdk=%s or recompile against api %s", self.ndk_api, self.min_sdk_version)
            raise Exception('You must pass --allow-minsdk-ndkapi-mismatch to build with --minsdk different to the target NDK api from the build step')
        self.private_dir = Path(config.private.dir)
        self.android_api = config.android.api
        self.app_name = config.android.app_name
        self.presplash_color = config.android.presplash_color
        self.bootstrapname = config.bootstrap.name # TODO: Use polymorphism.
        self.android_project_dir = Path(config.android.project.dir)
        self.version = config.version
        self.webview_port = config.webview.port
        self.sdl2_launchMode = config.sdl2.launchMode
        self.sdl2_activity_name = config.sdl2.activity.name
        self.icon_path = config.icon.full.path
        self.presplash_path = config.presplash.full.path
        self.wakelock = config.android.wakelock
        self.permissions = config.android.permissions.list()
        self.android_apptheme = config.android.apptheme
        self.fullscreen = config.fullscreen
        self.orientation = config.orientation
        self.package = config.android.package
        self.res_dir = Path(config.android.project.res.dir)
        self.config = config
        self.arch = arch
        self.platform = platform
        self.assetarchive = assetarchive
        self.mode = mode
        self.bootstrap = bootstrap

    def _numver(self):
        version_code = 0
        for i in self.version.split('.'):
            version_code *= 100
            version_code += int(i)
        return f"{self.arch.numver}{self.min_sdk_version}{version_code}"

    def _update_libraries_references(self): # XXX: Redundant?
        p = Properties()
        project_fn = self.android_project_dir / 'project.properties'
        with project_fn.open('rb') as f:
            p.load(f)
        for key in [k for k in p if k.startswith('android.library.reference.')]:
            del p[key]
        with project_fn.open('wb') as f:
            p.store(f)
        log.debug('project.properties updated')

    def _copy_application_sources(self):
        topath = self.private_dir.mkdirp() / 'main.py'
        log.debug("Create: %s", topath)
        self.config.processtemplate(resource_filename(skel.__name__, 'main.py.aridt'), topath)
        with resource_stream(skel.__name__, 'sitecustomize.py') as f, (self.private_dir / 'sitecustomize.py').open('wb') as g:
            shutil.copyfileobj(f, g)
        main_py = self.private_dir / 'service' / 'main.py'
        if main_py.exists(): # XXX: Why would it?
            with open(main_py, 'rb') as fd:
                data = fd.read()
            with open(main_py, 'wb') as fd:
                fd.write(b'import sys, os; sys.path = [os.path.join(os.getcwd(),"..", "_applibs")] + sys.path\n')
                fd.write(data)
            log.info('Patched service/main.py to include applibs')
        with (self.private_dir / 'p4a_env_vars.txt').open('w') as f:
            if self.bootstrapname != 'service_only':
                print(f"P4A_IS_WINDOWED={not self.fullscreen}", file = f)
                print(f"P4A_ORIENTATION={self.orientation}", file = f)
            print(f"P4A_MINSDK={self.min_sdk_version}", file = f)
        compileall(self.private_dir)

    @types(BundleOK, this = AndroidProjectOK) # XXX: Surely this depends on a few things, logically?
    def prepare(self, _):
        self._update_libraries_references()
        self._copy_application_sources()
        self.assetarchive.makeprivate()
        shutil.copy(self.icon_path, (self.res_dir / 'drawable').mkdirp() / 'icon.png')
        if self.bootstrapname != 'service_only':
            shutil.copy(self.presplash_path, self.res_dir / 'drawable' / 'presplash.jpg')
        numeric_version = self._numver()
        configChanges = ['keyboardHidden', 'orientation']
        if self.bootstrapname != 'service_only':
            configChanges += ['mcc', 'mnc', 'locale', 'touchscreen', 'keyboard', 'navigation', 'screenLayout', 'fontScale', 'uiMode']
            if self.min_sdk_version >= 8:
                configChanges += ['uiMode']
            if self.min_sdk_version >= 13:
                configChanges += ['screenSize', 'smallestScreenSize']
            if self.min_sdk_version >= 17:
                configChanges += ['layoutDirection']
            if self.min_sdk_version >= 24:
                configChanges += ['density']
        else:
            if self.min_sdk_version >= 13:
                configChanges += ['screenSize']
        with Repl() as repl:
            repl('" = $(xmlattr)')
            if self.bootstrapname == 'sdl2':
                repl.printf("launchMode = %s", self.sdl2_launchMode)
                repl.printf("activity name = %s", self.sdl2_activity_name)
            if self.bootstrapname != 'service_only':
                repl.printf("orientation = %s", self.orientation)
            repl.printf("xlargeScreens = %s", 'true' if self.min_sdk_version >= 9 else 'false')
            repl.printf("package = %s", self.package)
            repl.printf("versionCode = %s", numeric_version)
            repl.printf("versionName = %s", self.version)
            repl.printf("minSdkVersion = %s", self.min_sdk_version)
            repl('permissions := $list()')
            for p in self.permissions:
                repl.printf("permissions += %s", p)
            if self.wakelock:
                repl('permissions += android.permission.WAKE_LOCK')
            repl.printf("theme = %s", f"{self.android_apptheme}{'.Fullscreen' if self.fullscreen else ''}")
            repl.printf("wakelock = %s", int(self.wakelock))
            repl.printf("targetSdkVersion = %s", self.android_api)
            repl.printf("configChanges = %s", '|'.join(configChanges))
            repl.printf("redirect %s", self.android_project_dir / 'src' / 'main' / 'AndroidManifest.xml')
            repl.printf("< %s", self.bootstrap.templatepath('AndroidManifest.xml.aridt'))
        with Repl() as repl:
            repl('" = $(groovystr)')
            repl.printf("compileSdkVersion = %s", self.android_api)
            repl.printf("targetSdkVersion = %s", self.android_api)
            repl.printf("buildToolsVersion = %s", self.platform.build_tools_version())
            repl.printf("minSdkVersion = %s", self.min_sdk_version)
            repl.printf("versionCode = %s", numeric_version)
            repl.printf("versionName = %s", self.version)
            if self.mode.signing:
                repl('signingConfig name = Cowpox')
                repl.printf("storeFile = %s", os.environ['P4A_RELEASE_KEYSTORE']) # TODO: Get from config instead.
                repl.printf("keyAlias = %s", os.environ['P4A_RELEASE_KEYALIAS'])
                repl.printf("storePassword = %s", os.environ['P4A_RELEASE_KEYSTORE_PASSWD'])
                repl.printf("keyPassword = %s", os.environ['P4A_RELEASE_KEYALIAS_PASSWD'])
            repl.printf("redirect %s", self.android_project_dir / 'build.gradle')
            repl.printf("< %s", self.bootstrap.templatepath('build.gradle.aridt'))
        with Repl() as repl:
            repl('& = $(xmltext)')
            repl.printf("app_name = %s", self.app_name)
            repl.printf("private_version = %s", time.time()) # XXX: Must we use time?
            repl.printf("presplash_color = %s", self.presplash_color)
            repl('urlScheme = kivy')
            repl.printf("redirect %s", (self.res_dir / 'values').mkdirp() / 'strings.xml')
            repl.printf("< %s", self.bootstrap.templatepath('strings.xml.aridt'))
        if self.bootstrapname == 'webview':
            with Repl() as repl:
                repl.printf("port = %s", self.webview_port)
                repl.printf("redirect %s", (self.android_project_dir / 'src' / 'main' / 'java' / 'org' / 'kivy' / 'android').mkdirp() / 'WebViewLoader.java')
                repl.printf("< %s", self.bootstrap.templatepath('WebViewLoader.java.aridt'))
