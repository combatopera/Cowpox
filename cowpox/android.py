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

from . import skel
from .config import Config
from .platform import Platform
from aridimpl.model import Function, Text
from aridity import Repl
from diapyr import types
from fnmatch import fnmatch
from jproperties import Properties
from lagoon import gradle, patch
from lagoon.program import Program
from p4a import Arch, Graph, GraphInfo
from pathlib import Path
from pkg_resources import resource_filename, resource_stream, resource_string
from tempfile import TemporaryDirectory
import aridity, logging, os, shutil, subprocess, tarfile, time

log = logging.getLogger(__name__)

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

class APKPath: pass

class AndroidProjectOK: pass

class Assembly:

    @types(Config, AndroidProjectOK)
    def __init__(self, config, _):
        self.arch = config.android.arch
        self.dist_name = config.package.name
        self.releasemode = 'debug' != config.build_mode
        self.version = config.version
        self.commit = config.commit
        self.apkdir = Path(config.apk.dir)
        self.android_project_dir = Path(config.android.project.dir)
        self.gradleenv = dict(ANDROID_NDK_HOME = config.android_ndk_dir, ANDROID_HOME = config.android_sdk_dir)

    def build_package(self):
        gradle.__no_daemon.print('assembleRelease' if self.releasemode else 'assembleDebug', env = self.gradleenv, cwd = self.android_project_dir)
        if not self.releasemode:
            mode_sign = mode = 'debug'
        else:
            mode_sign = 'release'
            mode = 'release' if _check_p4a_sign_env(False) else 'release-unsigned'
        apkpath = self.apkdir / f"{self.dist_name}-{self.version}-{self.commit}-{self.arch}-{mode}.apk"
        shutil.copyfile(self.android_project_dir / 'build' / 'outputs' / 'apk' / mode_sign / f"{self.android_project_dir.name}-{mode}.apk", apkpath)
        log.info('Android packaging done!')
        return apkpath

@types(Assembly, AndroidProjectOK, this = APKPath)
def getapkpath(assembly, _):
    return assembly.build_package()

class AssetArchive:

    @types(Config, GraphInfo, Graph)
    def __init__(self, config, graphinfo, graph):
        self.assets_dir = Path(config.android.project.assets.dir)
        self.WHITELIST_PATTERNS = ['pyconfig.h'] if config.p4a.bootstrap in {'sdl2', 'webview', 'service_only'} else []
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
        if config.p4a.bootstrap in {'webview', 'service_only'} or 'sqlite3' not in graphinfo.recipenames:
            self.BLACKLIST_PATTERNS += ['sqlite3/*', 'lib-dynload/_sqlite3.so']
        self.graph = graph

    def _has(self, name):
        def match_filename(pattern_list):
            for pattern in pattern_list:
                if pattern.startswith('^'):
                    pattern = pattern[1:]
                else:
                    pattern = '*/' + pattern
                if fnmatch(name, pattern):
                    return True
        return not match_filename(self.WHITELIST_PATTERNS) and match_filename(self.BLACKLIST_PATTERNS)

    def makeprivate(self, source_dirs):
        for tfn in (self.assets_dir / n for n in ['public.mp3', 'private.mp3']):
            if tfn.exists():
                tfn.unlink()
        files = []
        compileall = Program.text(self.graph.host_recipe.python_exe)._OO._m.compileall._b._f
        for sd in source_dirs:
            sd = sd.resolve()
            for path in sd.rglob('*.py'):
                os.utime(path, (0, 0)) # Determinism.
            compileall.print(sd)
            files.extend([x, x.resolve().relative_to(sd)] for x in self._listfiles(sd) if not self._has(x))
        with tarfile.open(tfn.pmkdirp(), 'w:gz', format = tarfile.USTAR_FORMAT) as tf:
            dirs = set()
            for fn, afn in files:
                dn = afn.parent
                if dn not in dirs:
                    d = Path('.')
                    for component in dn.parent, dn.name:
                        d /= component
                        if d != Path('.') and d not in dirs:
                            dirs.add(d)
                            tinfo = tarfile.TarInfo(str(d))
                            tinfo.type = tarfile.DIRTYPE
                            tinfo.mode |= 0o111
                            tf.addfile(tinfo)
                tf.add(fn, afn)

    @classmethod
    def _listfiles(cls, d):
        subdirlist = []
        for fn in d.iterdir():
            if fn.is_file():
                yield fn
            else:
                subdirlist.append(fn)
        for subdir in subdirlist:
            yield from cls._listfiles(subdir)

def _xmltext(context, resolvable):
    from xml.sax.saxutils import escape
    return Text(escape(resolvable.resolve(context).cat())) # FIXME LATER: Insufficient for attr content.

def _xmlattr(context, resolvable):
    from xml.sax.saxutils import quoteattr
    return Text(quoteattr(resolvable.resolve(context).cat()))

class AndroidProject:

    @types(Config, Arch, Platform, AssetArchive)
    def __init__(self, config, arch, platform, assetarchive):
        self.ndk_api = config.android.ndk_api
        self.min_sdk_version = config.android.minapi
        if self.ndk_api != self.min_sdk_version:
            log.warning("--minsdk argument does not match the api that is compiled against. Only proceed if you know what you are doing, otherwise use --minsdk=%s or recompile against api %s", self.ndk_api, self.min_sdk_version)
            raise Exception('You must pass --allow-minsdk-ndkapi-mismatch to build with --minsdk different to the target NDK api from the build step')
        self.app_dir = Path(config.app_dir)
        self.android_api = config.android.api
        self.title = config.title
        self.presplash_color = config.android.presplash_color
        self.bootstrapname = config.p4a.bootstrap # TODO: Use polymorphism.
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
        self.fqpackage = config.package.fq
        self.res_dir = Path(config.android.project.res.dir)
        self.sign = 'debug' != config.build_mode and _check_p4a_sign_env(True)
        self.config = config
        self.arch = arch
        self.platform = platform
        self.assetarchive = assetarchive

    def _numver(self):
        version_code = 0
        for i in self.version.split('.'):
            version_code *= 100
            version_code += int(i)
        return f"{self.arch.numver}{self.min_sdk_version}{version_code}"

    def _update_libraries_references(self):
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
        topath = self.app_dir.mkdirp() / 'main.py'
        log.debug("Create: %s", topath)
        self.config.processtemplate(resource_filename(skel.__name__, 'main.py.aridt'), topath)
        with resource_stream(skel.__name__, 'sitecustomize.py') as f, (self.app_dir / 'sitecustomize.py').open('wb') as g:
            shutil.copyfileobj(f, g)
        main_py = self.app_dir / 'service' / 'main.py'
        if main_py.exists(): # XXX: Why would it?
            with open(main_py, 'rb') as fd:
                data = fd.read()
            with open(main_py, 'wb') as fd:
                fd.write(b'import sys, os; sys.path = [os.path.join(os.getcwd(),"..", "_applibs")] + sys.path\n')
                fd.write(data)
            log.info('Patched service/main.py to include applibs')

    def prepare(self):
        self._update_libraries_references()
        self._copy_application_sources()
        with TemporaryDirectory() as env_vars_tarpath:
            env_vars_tarpath = Path(env_vars_tarpath)
            with (env_vars_tarpath / 'p4a_env_vars.txt').open('w') as f:
                if self.bootstrapname != 'service_only':
                    print(f"P4A_IS_WINDOWED={not self.fullscreen}", file = f)
                    print(f"P4A_ORIENTATION={self.orientation}", file = f)
                print(f"P4A_MINSDK={self.min_sdk_version}", file = f)
            tar_dirs = [env_vars_tarpath, self.app_dir]
            for python_bundle_dir in (self.android_project_dir / n for n in ['private', '_python_bundle']):
                if python_bundle_dir.exists():
                    tar_dirs.append(python_bundle_dir)
            if self.bootstrapname == 'webview':
                tar_dirs.append(self.android_project_dir / 'webview_includes')
            self.assetarchive.makeprivate(tar_dirs)
        shutil.copy(self.icon_path, (self.res_dir / 'drawable').mkdirp() / 'icon.png')
        if self.bootstrapname != 'service_only':
            shutil.copy(self.presplash_path, self.res_dir / 'drawable' / 'presplash.jpg')
        numeric_version = self._numver()
        url_scheme = 'kivy'
        configChanges = []
        if self.bootstrapname != 'service_only':
            configChanges.append('mcc|mnc|locale|touchscreen|keyboard|keyboardHidden|navigation|orientation|screenLayout|fontScale|uiMode')
            if self.min_sdk_version >= 8:
                configChanges.append('uiMode')
            if self.min_sdk_version >= 13:
                configChanges.append('screenSize|smallestScreenSize')
            if self.min_sdk_version >= 17:
                configChanges.append('layoutDirection')
            if self.min_sdk_version >= 24:
                configChanges.append('density')
        else:
            configChanges.append('keyboardHidden|orientation')
            if self.min_sdk_version >= 13:
                configChanges.append('screenSize')
        c = aridity.Context()
        c['"',] = Function(_xmlattr)
        with Repl(c) as repl:
            if self.bootstrapname == 'sdl2':
                repl.printf("url_scheme = %s", url_scheme)
                repl.printf("launchMode = %s", self.sdl2_launchMode)
                repl.printf("activity name = %s", self.sdl2_activity_name)
            if self.bootstrapname != 'service_only':
                repl.printf("orientation = %s", self.orientation)
            repl.printf("xlargeScreens = %s", 'true' if self.min_sdk_version >= 9 else 'false')
            repl.printf("package = %s", self.fqpackage)
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
            repl.printf("android_api = %s", self.android_api)
            repl.printf("configChanges = %s", '|'.join(configChanges))
            repl.printf("redirect %s", self.android_project_dir / 'src' / 'main' / 'AndroidManifest.xml')
            repl.printf("< %s", self.android_project_dir / 'templates' / 'AndroidManifest.xml.aridt')
        c = aridity.Context()
        with Repl(c) as repl:
            repl('" = $(groovystr)')
            repl.printf("android_api = %s", self.android_api)
            repl.printf("build_tools_version = %s", self.platform.build_tools_version())
            repl.printf("minSdkVersion = %s", self.min_sdk_version)
            repl.printf("versionCode = %s", numeric_version)
            repl.printf("versionName = %s", self.version)
            if self.sign:
                repl('signingConfig = release')
                repl.printf("P4A_RELEASE_KEYSTORE = %s", os.environ['P4A_RELEASE_KEYSTORE']) # TODO: Get from config instead.
                repl.printf("P4A_RELEASE_KEYALIAS = %s", os.environ['P4A_RELEASE_KEYALIAS'])
                repl.printf("P4A_RELEASE_KEYSTORE_PASSWD = %s", os.environ['P4A_RELEASE_KEYSTORE_PASSWD'])
                repl.printf("P4A_RELEASE_KEYALIAS_PASSWD = %s", os.environ['P4A_RELEASE_KEYALIAS_PASSWD'])
            repl.printf("redirect %s", self.android_project_dir / 'build.gradle')
            repl.printf("< %s", self.android_project_dir / 'templates' / 'build.gradle.aridt')
        c = aridity.Context()
        c['&',] = Function(_xmltext)
        with Repl(c) as repl:
            repl.printf("app_name = %s", self.title)
            repl.printf("private_version = %s", time.time()) # XXX: Must we use time?
            repl.printf("presplash_color = %s", self.presplash_color)
            repl.printf("urlScheme = %s", url_scheme)
            repl.printf("redirect %s", (self.res_dir / 'values').mkdirp() / 'strings.xml')
            repl.printf("< %s", self.android_project_dir / 'templates' / 'strings.xml.aridt')
        if self.bootstrapname == 'webview':
            c = aridity.Context()
            with Repl(c) as repl:
                repl.printf("port = %s", self.webview_port)
                repl.printf("redirect %s", (self.android_project_dir / 'src' / 'main' / 'java' / 'org' / 'kivy' / 'android').mkdirp() / 'WebViewLoader.java')
                repl.printf("< %s", self.android_project_dir / 'templates' / 'WebViewLoader.tmpl.java')
        src_patches = self.android_project_dir / 'src' / 'patches'
        if src_patches.exists():
            log.info("Applying Java source code patches...")
            for patch_path in src_patches.iterdir():
                log.info("Applying patch: %s", patch_path)
                try:
                    patch._N._p1._t._i.print(patch_path, cwd = self.android_project_dir)
                except subprocess.CalledProcessError as e:
                    if e.returncode != 1:
                        raise e
                    log.warning("Failed to apply patch (exit code 1), assuming it is already applied: %s", patch_path)

class BulkOK: pass

@types(AndroidProject, BulkOK, this = AndroidProjectOK)
def prepareandroidproject(project, _):
    project.prepare()
