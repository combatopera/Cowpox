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
import aridity, jinja2, logging, os, shutil, subprocess, tarfile, time

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

class Render:

    def __init__(self, distdir):
        self.environment = jinja2.Environment(loader = jinja2.FileSystemLoader(distdir / 'templates'))

    def __call__(self, template, dest, **kwargs):
        dest.pmkdirp().write_text(self.environment.get_template(template).render(**kwargs))

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

def _xmlquote(context, resolvable):
    from xml.sax.saxutils import escape
    return Text(escape(resolvable.resolve(context).cat())) # FIXME LATER: Insufficient for attributes.

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
        distdir = self.dist_dir
        render = Render(distdir)
        blacklist = Blacklist(self.bootstrapname)
        if self.ndk_api != self.min_sdk_version:
            log.warning("--minsdk argument does not match the api that is compiled against. Only proceed if you know what you are doing, otherwise use --minsdk=%s or recompile against api %s", self.ndk_api, self.min_sdk_version)
            raise Exception('You must pass --allow-minsdk-ndkapi-mismatch to build with --minsdk different to the target NDK api from the build step')
        with (distdir / 'blacklist.txt').open() as f:
            blacklist.BLACKLIST_PATTERNS += [x for x in (l.strip() for l in f.read().splitlines()) if x and not x.startswith('#')]
        with (distdir / 'whitelist.txt').open() as f:
            blacklist.WHITELIST_PATTERNS += [x for x in (l.strip() for l in f.read().splitlines()) if x and not x.startswith('#')]
        if self.bootstrapname != 'webview':
            if not (self.app_dir / 'main.py').exists() and not (self.app_dir / 'main.pyo').exists():
                raise Exception('No main.py(o) found in your app directory. This file must exist to act as the entry point for you app. If your app is started by a file with a different name, rename it to main.py or add a main.py that loads it.')
        assets_dir = (distdir / 'src' / 'main' / 'assets').mkdirp()
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
            for python_bundle_dir in (distdir / n for n in ['private', '_python_bundle']):
                if python_bundle_dir.exists():
                    tar_dirs.append(python_bundle_dir)
            if self.bootstrapname == 'webview':
                tar_dirs.append(distdir / 'webview_includes')
            _make_tar(assets_dir / 'private.mp3', tar_dirs, blacklist, self.graph.host_recipe.python_exe)
        res_dir = distdir / 'src' / 'main' / 'res'
        default_icon = distdir / 'templates' / 'kivy-icon.png'
        shutil.copy(args.icon or default_icon, res_dir / 'drawable' / 'icon.png')
        if self.bootstrapname != 'service_only':
            default_presplash = distdir / 'templates' / 'kivy-presplash.jpg'
            shutil.copy(args.presplash or default_presplash, res_dir / 'drawable' / 'presplash.jpg')
        args.numeric_version = self._numver(args) # TODO: Do not abuse args for this.
        service_names = []
        for sid, spec in enumerate(args.services):
            name, entrypoint, *options = spec.split(':')
            service_names.append(name)
            render(
                'Service.tmpl.java',
                distdir / 'src' / 'main' / 'java' / args.package.replace('.', os.sep) / f"Service{name.capitalize()}.java",
                name = name,
                entrypoint = entrypoint,
                args = args,
                foreground = 'foreground' in options,
                sticky = 'sticky' in options,
                service_id = 1 + sid,
            )
        url_scheme = 'kivy'
        render_args = {
            "args": args,
            "service": any((self.app_dir / 'service' / name).exists() for name in ['main.py', 'main.pyo']),
            "service_names": service_names,
            "android_api": self.android_api,
        }
        if self.bootstrapname == 'sdl2':
            render_args["url_scheme"] = url_scheme
        render(
            'AndroidManifest.tmpl.xml',
            self.dist_dir / 'src' / 'main' / 'AndroidManifest.xml',
            **render_args,
        )
        c = aridity.Context()
        with Repl(c) as repl:
            repl('" = $(groovystr)')
            repl.printf("android_api = %s", self.android_api)
            repl.printf("build_tools_version = %s", self.platform.build_tools_version())
            repl.printf("min_sdk_version = %s", args.min_sdk_version)
            repl.printf("numeric_version = %s", args.numeric_version)
            repl.printf("version = %s", args.version)
            if args.sign:
                repl('signingConfig = release')
                repl.printf("P4A_RELEASE_KEYSTORE = %s", os.environ['P4A_RELEASE_KEYSTORE']) # TODO: Get from config instead.
                repl.printf("P4A_RELEASE_KEYALIAS = %s", os.environ['P4A_RELEASE_KEYALIAS'])
                repl.printf("P4A_RELEASE_KEYSTORE_PASSWD = %s", os.environ['P4A_RELEASE_KEYSTORE_PASSWD'])
                repl.printf("P4A_RELEASE_KEYALIAS_PASSWD = %s", os.environ['P4A_RELEASE_KEYALIAS_PASSWD'])
            repl.printf("redirect %s", distdir / 'build.gradle')
            repl.printf("< %s", self.dist_dir / 'templates' / 'build.gradle.aridt')
        c = aridity.Context()
        c['"',] = Function(_xmlquote)
        with Repl(c) as repl:
            repl.printf("app_name = %s", self.title)
            repl.printf("private_version = %s", time.time()) # XXX: Must we use time?
            repl.printf("presplash_color = %s", self.presplash_color)
            repl.printf("urlScheme = %s", url_scheme)
            repl.printf("redirect %s", (res_dir / 'values' / 'strings.xml').pmkdirp())
            repl.printf("< %s", self.dist_dir / 'templates' / 'strings.xml.aridt')
        if self.bootstrapname == 'webview':
            render(
                'WebViewLoader.tmpl.java',
                distdir / 'src' / 'main' / 'java' / 'org' / 'kivy' / 'android' / 'WebViewLoader.java',
                args = args,
            )
        src_patches = distdir / 'src' / 'patches'
        if src_patches.exists():
            log.info("Applying Java source code patches...")
            for patch_path in src_patches.iterdir():
                log.info("Applying patch: %s", patch_path)
                try:
                    patch._N._p1._t._i.print(patch_path, cwd = distdir)
                except subprocess.CalledProcessError as e:
                    if e.returncode != 1:
                        raise e
                    log.warning("Failed to apply patch (exit code 1), assuming it is already applied: %s", patch_path)
