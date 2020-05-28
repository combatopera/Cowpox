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

from distutils.version import LooseVersion
from fnmatch import fnmatch
from lagoon import patch
from pathlib import Path
from tempfile import TemporaryDirectory
import jinja2, json, logging, os, shutil, subprocess, tarfile, time

log = logging.getLogger(__name__)

class DistInfo:

    def __init__(self, distdir):
        with (distdir / 'dist_info.json').open() as f:
            self.d = json.load(f)

    def forkey(self, key):
        return self.d[key]

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

def _try_unlink(fn):
    if fn.exists():
        fn.unlink()

class Render:

    def __init__(self, distdir):
        self.environment = jinja2.Environment(loader = jinja2.FileSystemLoader(distdir / 'templates'))

    def __call__(self, template, dest, **kwargs):
        dest.parent.mkdirp()
        dest.write_text(self.environment.get_template(template).render(**kwargs))

def _listfiles(d):
    subdirlist = []
    for fn in d.iterdir():
        if fn.is_file():
            yield fn
        else:
            subdirlist.append(fn)
    for subdir in subdirlist:
        yield from _listfiles(subdir)

def _make_tar(tfn, source_dirs, blacklist, distinfo):
    files = []
    for sd in source_dirs:
        sd = sd.resolve()
        subprocess.check_call([distinfo.forkey('hostpython'), '-OO', '-m', 'compileall', '-b', '-f', sd])
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

def makeapkversion(args, distdir, private):
    render = Render(distdir)
    distinfo = DistInfo(distdir)
    ndk_api = int(distinfo.forkey('ndk_api'))
    bootstrapname = distinfo.forkey('bootstrap')
    blacklist = Blacklist(bootstrapname)
    args.allow_backup = 'true'
    args.extra_manifest_xml = ''
    if ndk_api != args.min_sdk_version:
        log.warning("--minsdk argument does not match the api that is compiled against. Only proceed if you know what you are doing, otherwise use --minsdk=%s or recompile against api %s", ndk_api, args.min_sdk_version)
        raise Exception('You must pass --allow-minsdk-ndkapi-mismatch to build with --minsdk different to the target NDK api from the build step')
    with (distdir / 'blacklist.txt').open() as f:
        blacklist.BLACKLIST_PATTERNS += [x for x in (l.strip() for l in f.read().splitlines()) if x and not x.startswith('#')]
    with (distdir / 'whitelist.txt').open() as f:
        blacklist.WHITELIST_PATTERNS += [x for x in (l.strip() for l in f.read().splitlines()) if x and not x.startswith('#')]
    args.private = private
    if bootstrapname != "webview":
        if not (private.resolve() / 'main.py').exists() and not (private.resolve() / 'main.pyo').exists():
            raise Exception('No main.py(o) found in your app directory. This file must exist to act as the entry point for you app. If your app is started by a file with a different name, rename it to main.py or add a main.py that loads it.')
    assets_dir = (distdir / 'src' / 'main' / 'assets').mkdirp()
    _try_unlink(assets_dir / 'public.mp3')
    _try_unlink(assets_dir / 'private.mp3')
    with TemporaryDirectory() as env_vars_tarpath:
        env_vars_tarpath = Path(env_vars_tarpath)
        with (env_vars_tarpath / 'p4a_env_vars.txt').open('w') as f:
            if bootstrapname != 'service_only':
                print(f"P4A_IS_WINDOWED={args.window}", file = f)
                print(f"P4A_ORIENTATION={args.orientation}", file = f)
            print(f"P4A_MINSDK={args.min_sdk_version}", file = f)
        tar_dirs = [env_vars_tarpath, private]
        for python_bundle_dir in (distdir / n for n in ['private', '_python_bundle']):
            if python_bundle_dir.exists():
                tar_dirs.append(python_bundle_dir)
        if bootstrapname == "webview":
            tar_dirs.append(distdir / 'webview_includes')
        _make_tar(assets_dir / 'private.mp3', tar_dirs, blacklist, distinfo)
    res_dir = distdir / 'src' / 'main' / 'res'
    default_icon = distdir / 'templates' / 'kivy-icon.png'
    shutil.copy(args.icon or default_icon, res_dir / 'drawable' / 'icon.png')
    if bootstrapname != "service_only":
        default_presplash = distdir / 'templates' / 'kivy-presplash.jpg'
        shutil.copy(args.presplash or default_presplash, res_dir / 'drawable' / 'presplash.jpg')
    def numver():
        version_code = 0
        for i in args.version.split('.'):
            version_code *= 100
            version_code += int(i)
        lookup = {'x86_64': 9, 'arm64-v8a': 8, 'armeabi-v7a': 7, 'x86': 6}
        return f"{lookup.get(distinfo.forkey('archs')[0], 1)}{args.min_sdk_version}{version_code}"
    args.numeric_version = numver() # TODO: Do not abuse args for this.
    if args.intent_filters:
        args.intent_filters = args.intent_filters.read_text()
    args.extra_source_dirs = []
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
    android_api = int((distdir / 'project.properties').read_text().strip().split('-')[1])
    sdk_dir = Path((distdir / 'local.properties').read_text().strip()[8:])
    ignored = {".DS_Store", ".ds_store"}
    build_tools_version = max((x.name for x in (sdk_dir / 'build-tools').iterdir() if x.name not in ignored), key = LooseVersion)
    url_scheme = 'kivy'
    manifest_path = distdir / 'src' / 'main' / 'AndroidManifest.xml'
    render_args = {
        "args": args,
        "service": any((args.private.resolve() / 'service' / name).exists() for name in ['main.py', 'main.pyo']),
        "service_names": service_names,
        "android_api": android_api
    }
    if bootstrapname == "sdl2":
        render_args["url_scheme"] = url_scheme
    render(
        'AndroidManifest.tmpl.xml',
        manifest_path,
        **render_args,
    )
    render(
        'build.tmpl.gradle',
        distdir / 'build.gradle',
        args = args,
        aars = [],
        jars = [],
        android_api = android_api,
        build_tools_version = build_tools_version,
    )
    render_args = {"args": args, "private_version": str(time.time())}
    if bootstrapname == "sdl2":
        render_args["url_scheme"] = url_scheme
    render(
        'strings.tmpl.xml',
        res_dir / 'values' / 'strings.xml',
        **render_args,
    )
    if (distdir / "templates" / "custom_rules.tmpl.xml").exists():
        render(
            'custom_rules.tmpl.xml',
            distdir / 'custom_rules.xml',
            args = args,
        )
    if bootstrapname == "webview":
        render(
            'WebViewLoader.tmpl.java',
            distdir / 'src' / 'main' / 'java' / 'org' / 'kivy' / 'android' / 'WebViewLoader.java',
            args = args,
        )
    if args.sign:
        render('build.properties', distdir / 'build.properties')
    elif (distdir / 'build.properties').exists():
        (distdir / 'build.properties').unlink()
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
