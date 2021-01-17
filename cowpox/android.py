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

from . import AndroidProjectMemo, APKPath, Arch, JavaSrc, LibRepo, PrivateMemo, RecipeMemo
from .make import Make
from .platform import Platform
from .recipes.sqlite3 import Sqlite3Recipe
from .util import Contrib, writeproperties
from aridity import Repl
from aridity.config import Config
from diapyr import types
from diapyr.util import enum
from fnmatch import fnmatch
from itertools import chain
from lagoon import unzip
from pathlib import Path
from pkg_resources import resource_string
from tempfile import TemporaryDirectory
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

    @types(Config, BuildMode)
    def __init__(self, config, mode):
        self.android_project_dir = Path(config.android.project.dir)
        self.gradleenv = dict(ANDROID_HOME = config.SDK.dir, ANDROID_NDK_HOME = config.NDK.dir)
        self.gradle_builddir = Path(config.gradle.buildDir)
        self.mode = mode

    @types(Make, AndroidProjectMemo, this = APKPath)
    def build_package(self, make, projectmemo):
        make(self.gradle_builddir, [projectmemo, self.mode.name], self._target) # XXX: Should SDK/NDK be in dependencies?
        # XXX: Can we tell gradle what to use for filename?
        return self.gradle_builddir / 'outputs' / 'apk' / self.mode.division.name / f"{self.android_project_dir.name}-{self.mode.name}.apk"

    def _target(self):
        from lagoon import gradle
        # TODO: Download gradle dependencies in advance.
        gradle.__no_daemon[print](self.mode.division.goal, env = self.gradleenv, cwd = self.android_project_dir)
        log.info('Android packaging done!')

class AssetArchive:

    @types(Config, Sqlite3Recipe)
    def __init__(self, config, sqlite3 = None):
        self.contribs = [
            Contrib([Path(config.private.dir)]),
            Contrib([Path(d, 'private') for d in chain(config.bootstrap.dirs, config.bootstrap.common.dirs)]),
        ]
        self.tarpath = Path(config.android.project.assets.dir, 'private.mp3')
        self.WHITELIST_PATTERNS = ['pyconfig.h'] if config.bootstrap.name in {'sdl2', 'webview', 'service_only'} else []
        self.WHITELIST_PATTERNS.extend(config.android.whitelist)
        self.BLACKLIST_PATTERNS = [
            '^*.hg/*',
            '^*.git/*',
            '^*.bzr/*',
            '^*.svn/*',
            '~',
            '*.bak',
            '*.swp',
            '*.py',
            '.Cowpox/*',
        ] + resource_string(__name__, 'blacklist.txt').decode().splitlines()
        if config.bootstrap.name in {'webview', 'service_only'} or sqlite3 is None:
            self.BLACKLIST_PATTERNS += ['sqlite3/*', 'lib-dynload/_sqlite3.so']

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
            for contrib in self.contribs:
                for path, relpath in contrib.filepaths():
                    if self._accept(path):
                        mkdirp(relpath.parent)
                        tf.add(path, relpath)

class AndroidProject:

    @types(Config, Arch, Platform, AssetArchive, BuildMode, [JavaSrc], [LibRepo])
    def __init__(self, config, arch, platform, assetarchive, mode, javasrcs, librepos):
        ndk_api = config.android.ndk_api
        self.min_sdk_version = config.android.minSdkVersion
        if ndk_api != self.min_sdk_version:
            log.warning("--minsdk argument does not match the api that is compiled against. Only proceed if you know what you are doing, otherwise use --minsdk=%s or recompile against api %s", ndk_api, self.min_sdk_version)
            raise Exception('You must pass --allow-minsdk-ndkapi-mismatch to build with --minsdk different to the target NDK api from the build step')
        self.android_api = config.android.api
        self.app_name = config.android.app_name
        self.presplash_color = config.android.presplash_color
        self.bootstrapname = config.bootstrap.name # TODO: Use polymorphism.
        self.android_project_dir = Path(config.android.project.dir)
        self.android_project_libs = Path(config.android.project.jniLibs)
        self.version = config.version
        self.webview_port = config.webview.port
        self.sdl2_launchMode = config.sdl2.launchMode
        self.sdl2_activity_name = config.sdl2.activity.name
        self.icon_path = config.icon.full.path
        self.presplash_path = config.presplash.full.path
        self.wakelock = config.android.wakelock
        self.permissions = list(config.android.permissions)
        self.android_apptheme = config.android.apptheme
        self.fullscreen = config.android.fullscreen
        self.orientation = config.android.orientation
        self.package = config.android.package
        self.res_dir = Path(config.android.project.res.dir)
        self.gradle_builddir = config.gradle.buildDir
        self.sdk_dir = config.SDK.dir
        self.aar_dir = Path(config.aar.dir)
        self.srccontrib = Contrib([Path(d, 'src') for d in chain(config.bootstrap.dirs, config.bootstrap.common.dirs)])
        self.templates = Contrib([Path(d, 'templates') for d in chain(config.bootstrap.dirs, config.bootstrap.common.dirs)])
        self.arch = arch
        self.platform = platform
        self.assetarchive = assetarchive
        self.mode = mode
        self.javasrcs = javasrcs
        self.librepos = librepos

    def _numver(self):
        version_code = 0
        for i in self.version.split('.'):
            version_code *= 100
            version_code += int(i)
        return f"{self.arch.numver}{self.min_sdk_version}{version_code}"

    def _distribute_aars(self):
        log.info('Unpacking aars')
        for aar in self.aar_dir.glob('*.aar'):
            self._unpack_aar(aar)

    def _unpack_aar(self, aar):
        with TemporaryDirectory() as temp_dir:
            name = os.path.splitext(aar.name)[0]
            jar_name = f"{name}.jar"
            log.info("unpack %s aar", name)
            log.debug("  from %s", aar)
            log.debug("  to %s", temp_dir)
            unzip._o[print](aar, '-d', temp_dir)
            jar_src = Path(temp_dir, 'classes.jar')
            jar_tgt = self.android_project_libs.mkdirp() / jar_name
            log.debug("copy %s jar", name)
            log.debug("  from %s", jar_src)
            log.debug("  to %s", jar_tgt)
            shutil.copy2(jar_src, jar_tgt)
            so_src_dir = Path(temp_dir, 'jni', self.arch.name)
            so_tgt_dir = (self.android_project_libs / self.arch.name).mkdirp()
            log.debug("copy %s .so", name)
            log.debug("  from %s", so_src_dir)
            log.debug("  to %s", so_tgt_dir)
            for f in so_src_dir.glob('*.so'):
                shutil.copy2(f, so_tgt_dir)

    @types(Make, [RecipeMemo], PrivateMemo, this = AndroidProjectMemo)
    def prepare(self, make, recipememos, privatememo):
        return make(self.android_project_dir, [
            self.bootstrapname,
            self.android_api, # XXX: And sdk_dir?
            str(self.aar_dir), # XXX: Check what's in there?
            self.arch.name, # TODO: And most of the config.
            recipememos,
            privatememo,
        ], self._prepare)

    def _prepare(self):
        self.srccontrib.mergeinto(self.android_project_dir / 'src')
        writeproperties(self.android_project_dir / 'project.properties', target = f"android-{self.android_api}")
        writeproperties(self.android_project_dir / 'local.properties', **{'sdk.dir': self.sdk_dir}) # Required by gradle build.
        log.info('Copying libs.')
        self._distribute_aars()
        archlibs = (self.android_project_libs / self.arch.name).mkdirp()
        for librepo in self.librepos:
            for builtlibpath in librepo.builtlibpaths():
                shutil.copy2(librepo.recipebuilddir / builtlibpath, archlibs)
        for javasrc in self.javasrcs:
            contrib = javasrc.javasrc()
            log.info("Copying java files from: %s", contrib)
            contrib.mergeinto(self.android_project_dir / 'src' / 'main' / 'java')
        self.assetarchive.makeprivate()
        shutil.copy2(self.icon_path, (self.res_dir / 'drawable').mkdirp() / 'icon.png')
        if self.bootstrapname != 'service_only':
            shutil.copy2(self.presplash_path, self.res_dir / 'drawable' / 'presplash.jpg')
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
            repl.printf("< %s", self.templates.resolve('AndroidManifest.xml.aridt'))
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
            repl.printf("buildDir = %s", self.gradle_builddir)
            repl.printf("redirect %s", self.android_project_dir / 'build.gradle')
            repl.printf("< %s", self.templates.resolve('build.gradle.aridt'))
        with Repl() as repl:
            repl('& = $(xmltext)')
            repl.printf("app_name = %s", self.app_name)
            repl.printf("private_version = %s", time.time()) # XXX: Must we use time?
            repl.printf("presplash_color = %s", self.presplash_color)
            repl('urlScheme = kivy')
            repl.printf("redirect %s", (self.res_dir / 'values').mkdirp() / 'strings.xml')
            repl.printf("< %s", self.templates.resolve('strings.xml.aridt'))
        if self.bootstrapname == 'webview':
            with Repl() as repl:
                repl.printf("port = %s", self.webview_port)
                repl.printf("redirect %s", (self.android_project_dir / 'src' / 'main' / 'java' / 'org' / 'kivy' / 'android').mkdirp() / 'WebViewLoader.java')
                repl.printf("< %s", self.templates.resolve('WebViewLoader.java.aridt'))
