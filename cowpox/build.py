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
from .platform import Platform
from aridimpl.model import Function, Text
from aridity import Repl
from diapyr import types
from fnmatch import fnmatch
from lagoon import patch
from lagoon.program import Program
from p4a import Arch, Graph
from pathlib import Path
from tempfile import TemporaryDirectory
import aridity, logging, os, shutil, subprocess, tarfile, time

log = logging.getLogger(__name__)

class Blacklist:

    def __init__(self, bootstrapname):
        self.BLACKLIST_PATTERNS = [
            '^*.hg/*',
            '^*.git/*',
            '^*.bzr/*',
            '^*.svn/*',
            '~',
            '*.bak',
            '*.swp',
            '*.py',
        ]
        self.WHITELIST_PATTERNS = ['pyconfig.h'] if bootstrapname in {'sdl2', 'webview', 'service_only'} else []

    def has(self, name):
        def match_filename(pattern_list):
            for pattern in pattern_list:
                if pattern.startswith('^'):
                    pattern = pattern[1:]
                else:
                    pattern = '*/' + pattern
                if fnmatch(name, pattern):
                    return True
        return not match_filename(self.WHITELIST_PATTERNS) and match_filename(self.BLACKLIST_PATTERNS)

def _listfiles(d):
    subdirlist = []
    for fn in d.iterdir():
        if fn.is_file():
            yield fn
        else:
            subdirlist.append(fn)
    for subdir in subdirlist:
        yield from _listfiles(subdir)

def _make_tar(tfn, source_dirs, blacklist, hostpython):
    files = []
    compileall = Program.text(hostpython)._OO._m.compileall._b._f
    for sd in source_dirs:
        sd = sd.resolve()
        for path in sd.rglob('*.py'):
            os.utime(path, (0, 0)) # Determinism.
        compileall.print(sd)
        files.extend([x, x.resolve().relative_to(sd)] for x in _listfiles(sd) if not blacklist.has(x))
    with tarfile.open(tfn, 'w:gz', format = tarfile.USTAR_FORMAT) as tf:
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

def _xmltext(context, resolvable):
    from xml.sax.saxutils import escape
    return Text(escape(resolvable.resolve(context).cat())) # FIXME LATER: Insufficient for attr content.

def _xmlattr(context, resolvable):
    from xml.sax.saxutils import quoteattr
    return Text(quoteattr(resolvable.resolve(context).cat()))

class APKMaker:

    @types(Config, Graph, Arch, Platform)
    def __init__(self, config, graph, arch, platform):
        self.app_dir = Path(config.app_dir)
        self.ndk_api = config.android.ndk_api
        self.android_api = config.android.api
        self.min_sdk_version = config.android.minapi
        self.title = config.title
        self.presplash_color = config.android.presplash_color
        self.bootstrapname = config.p4a.bootstrap
        self.dist_dir = Path(config.dist_dir)
        self.graph = graph
        self.arch = arch
        self.platform = platform

    def _numver(self, args):
        version_code = 0
        for i in args.version.split('.'):
            version_code *= 100
            version_code += int(i)
        return f"{self.arch.numver}{self.min_sdk_version}{version_code}"

    def makeapkversion(self, args):
        blacklist = Blacklist(self.bootstrapname)
        if self.ndk_api != self.min_sdk_version:
            log.warning("--minsdk argument does not match the api that is compiled against. Only proceed if you know what you are doing, otherwise use --minsdk=%s or recompile against api %s", self.ndk_api, self.min_sdk_version)
            raise Exception('You must pass --allow-minsdk-ndkapi-mismatch to build with --minsdk different to the target NDK api from the build step')
        with (self.dist_dir / 'blacklist.txt').open() as f:
            blacklist.BLACKLIST_PATTERNS += [x for x in (l.strip() for l in f.read().splitlines()) if x and not x.startswith('#')]
        with (self.dist_dir / 'whitelist.txt').open() as f:
            blacklist.WHITELIST_PATTERNS += [x for x in (l.strip() for l in f.read().splitlines()) if x and not x.startswith('#')]
        if self.bootstrapname != 'webview':
            if not (self.app_dir / 'main.py').exists() and not (self.app_dir / 'main.pyo').exists():
                raise Exception('No main.py(o) found in your app directory. This file must exist to act as the entry point for you app. If your app is started by a file with a different name, rename it to main.py or add a main.py that loads it.')
        assets_dir = (self.dist_dir / 'src' / 'main' / 'assets').mkdirp()
        for p in (assets_dir / n for n in ['public.mp3', 'private.mp3']):
            if p.exists():
                p.unlink()
        with TemporaryDirectory() as env_vars_tarpath:
            env_vars_tarpath = Path(env_vars_tarpath)
            with (env_vars_tarpath / 'p4a_env_vars.txt').open('w') as f:
                if self.bootstrapname != 'service_only':
                    print(f"P4A_IS_WINDOWED={args.window}", file = f)
                    print(f"P4A_ORIENTATION={args.orientation}", file = f)
                print(f"P4A_MINSDK={self.min_sdk_version}", file = f)
            tar_dirs = [env_vars_tarpath, self.app_dir]
            for python_bundle_dir in (self.dist_dir / n for n in ['private', '_python_bundle']):
                if python_bundle_dir.exists():
                    tar_dirs.append(python_bundle_dir)
            if self.bootstrapname == 'webview':
                tar_dirs.append(self.dist_dir / 'webview_includes')
            _make_tar(assets_dir / 'private.mp3', tar_dirs, blacklist, self.graph.host_recipe.python_exe)
        res_dir = self.dist_dir / 'src' / 'main' / 'res'
        default_icon = self.dist_dir / 'templates' / 'kivy-icon.png'
        shutil.copy(args.icon or default_icon, res_dir / 'drawable' / 'icon.png')
        if self.bootstrapname != 'service_only':
            default_presplash = self.dist_dir / 'templates' / 'kivy-presplash.jpg'
            shutil.copy(args.presplash or default_presplash, res_dir / 'drawable' / 'presplash.jpg')
        args.numeric_version = self._numver(args) # TODO: Do not abuse args for this.
        url_scheme = 'kivy'
        configChanges = []
        if self.bootstrapname != 'service_only':
            configChanges.append('mcc|mnc|locale|touchscreen|keyboard|keyboardHidden|navigation|orientation|screenLayout|fontScale|uiMode')
            if args.min_sdk_version >= 8:
                configChanges.append('uiMode')
            if args.min_sdk_version >= 13:
                configChanges.append('screenSize|smallestScreenSize')
            if args.min_sdk_version >= 17:
                configChanges.append('layoutDirection')
            if args.min_sdk_version >= 24:
                configChanges.append('density')
        else:
            configChanges.append('keyboardHidden|orientation')
            if args.min_sdk_version >= 13:
                configChanges.append('screenSize')
        c = aridity.Context()
        c['"',] = Function(_xmlattr)
        with Repl(c) as repl:
            if self.bootstrapname == 'sdl2':
                repl.printf("url_scheme = %s", url_scheme)
                repl.printf("launchMode = %s", args.activity_launch_mode)
                repl.printf("android_entrypoint = %s", args.android_entrypoint)
            if self.bootstrapname != 'service_only':
                repl.printf("orientation = %s", args.orientation)
            repl.printf("xlargeScreens = %s", 'true' if self.min_sdk_version >= 9 else 'false')
            repl.printf("package = %s", args.package)
            repl.printf("versionCode = %s", args.numeric_version)
            repl.printf("versionName = %s", args.version)
            repl.printf("minSdkVersion = %s", args.min_sdk_version)
            for p in args.permissions:
                repl.printf("permissions += %s", p)
            repl.printf("theme = %s", f"{args.android_apptheme}{'' if args.window else '.Fullscreen'}")
            repl.printf("wakelock = %s", int(bool(args.wakelock)))
            repl.printf("android_api = %s", self.android_api)
            repl.printf("configChanges = %s", '|'.join(configChanges))
            repl.printf("redirect %s", self.dist_dir / 'src' / 'main' / 'AndroidManifest.xml')
            repl.printf("< %s", self.dist_dir / 'templates' / 'AndroidManifest.xml.aridt')
        c = aridity.Context()
        with Repl(c) as repl:
            repl('" = $(groovystr)')
            repl.printf("android_api = %s", self.android_api)
            repl.printf("build_tools_version = %s", self.platform.build_tools_version())
            repl.printf("min_sdk_version = %s", self.min_sdk_version)
            repl.printf("numeric_version = %s", args.numeric_version)
            repl.printf("version = %s", args.version)
            if args.sign:
                repl('signingConfig = release')
                repl.printf("P4A_RELEASE_KEYSTORE = %s", os.environ['P4A_RELEASE_KEYSTORE']) # TODO: Get from config instead.
                repl.printf("P4A_RELEASE_KEYALIAS = %s", os.environ['P4A_RELEASE_KEYALIAS'])
                repl.printf("P4A_RELEASE_KEYSTORE_PASSWD = %s", os.environ['P4A_RELEASE_KEYSTORE_PASSWD'])
                repl.printf("P4A_RELEASE_KEYALIAS_PASSWD = %s", os.environ['P4A_RELEASE_KEYALIAS_PASSWD'])
            repl.printf("redirect %s", self.dist_dir / 'build.gradle')
            repl.printf("< %s", self.dist_dir / 'templates' / 'build.gradle.aridt')
        c = aridity.Context()
        c['&',] = Function(_xmltext)
        with Repl(c) as repl:
            repl.printf("app_name = %s", self.title)
            repl.printf("private_version = %s", time.time()) # XXX: Must we use time?
            repl.printf("presplash_color = %s", self.presplash_color)
            repl.printf("urlScheme = %s", url_scheme)
            repl.printf("redirect %s", (res_dir / 'values' / 'strings.xml').pmkdirp())
            repl.printf("< %s", self.dist_dir / 'templates' / 'strings.xml.aridt')
        if self.bootstrapname == 'webview':
            c = aridity.Context()
            with Repl(c) as repl:
                repl.printf("port = %s", args.port)
                repl.printf("redirect %s", (self.dist_dir / 'src' / 'main' / 'java' / 'org' / 'kivy' / 'android').mkdirp() / 'WebViewLoader.java')
                repl.printf("< %s", self.dist_dir / 'templates' / 'WebViewLoader.tmpl.java')
        src_patches = self.dist_dir / 'src' / 'patches'
        if src_patches.exists():
            log.info("Applying Java source code patches...")
            for patch_path in src_patches.iterdir():
                log.info("Applying patch: %s", patch_path)
                try:
                    patch._N._p1._t._i.print(patch_path, cwd = self.dist_dir)
                except subprocess.CalledProcessError as e:
                    if e.returncode != 1:
                        raise e
                    log.warning("Failed to apply patch (exit code 1), assuming it is already applied: %s", patch_path)
