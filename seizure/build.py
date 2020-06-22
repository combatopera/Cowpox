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
from os import listdir, makedirs, remove
from os.path import dirname, join, isfile, realpath, relpath, split, exists
from pathlib import Path
from pythonforandroid.util import current_directory
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
        dest_dir = dirname(dest)
        if dest_dir and not exists(dest_dir):
            makedirs(dest_dir)
        text = self.environment.get_template(template).render(**kwargs)
        with open(dest, 'wb') as f:
            f.write(text.encode('utf-8'))

def _listfiles(d):
    basedir = d
    subdirlist = []
    for item in os.listdir(d):
        fn = join(d, item)
        if isfile(fn):
            yield fn
        else:
            subdirlist.append(join(basedir, item))
    for subdir in subdirlist:
        for fn in _listfiles(subdir):
            yield fn

def _make_tar(tfn, source_dirs, blacklist, distinfo):
    files = []
    for sd in source_dirs:
        sd = sd.resolve()
        subprocess.check_call([distinfo.forkey('hostpython'), '-OO', '-m', 'compileall', '-b', '-f', sd])
        files.extend([x, relpath(realpath(x), sd)] for x in _listfiles(sd) if not blacklist.has(x))
    with tarfile.open(tfn, 'w:gz', format = tarfile.USTAR_FORMAT) as tf:
        dirs = set()
        for fn, afn in files:
            dn = dirname(afn)
            if dn not in dirs:
                d = ''
                for component in split(dn):
                    d = join(d, component)
                    if d.startswith('/'):
                        d = d[1:]
                    if d == '' or d in dirs:
                        continue
                    dirs.add(d)
                    tinfo = tarfile.TarInfo(d)
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
    _make_package(args, bootstrapname, blacklist, distinfo, render, distdir, assets_dir)

def _make_package(args, bootstrapname, blacklist, distinfo, render, distdir, assets_dir):
  with current_directory(distdir):
    with TemporaryDirectory() as env_vars_tarpath:
        with Path(env_vars_tarpath, 'p4a_env_vars.txt').open('w') as f:
            if bootstrapname != 'service_only':
                print(f"P4A_IS_WINDOWED={args.window}", file = f)
                print(f"P4A_ORIENTATION={args.orientation}", file = f)
            print(f"P4A_MINSDK={args.min_sdk_version}", file = f)
        tar_dirs = [env_vars_tarpath]
        log.info('No setup.py/pyproject.toml used, copying full private data into .apk.')
        tar_dirs.append(args.private)
        for python_bundle_dir in 'private', '_python_bundle':
            if (distdir / python_bundle_dir).exists():
                tar_dirs.append(distdir / python_bundle_dir)
        if bootstrapname == "webview":
            tar_dirs.append(distdir / 'webview_includes')
        _make_tar(assets_dir / 'private.mp3', tar_dirs, blacklist, distinfo)
    res_dir = Path('src', 'main', 'res')
    default_icon = 'templates/kivy-icon.png'
    default_presplash = 'templates/kivy-presplash.jpg'
    shutil.copy(args.icon or default_icon, res_dir / 'drawable' / 'icon.png')
    if bootstrapname != "service_only":
        shutil.copy(args.presplash or default_presplash, res_dir / 'drawable' / 'presplash.jpg')
    versioned_name = args.name.replace(' ', '').replace('\'', '') + '-' + args.version
    def numver():
        version_code = 0
        for i in args.version.split('.'):
            version_code *= 100
            version_code += int(i)
        lookup = {'x86_64': 9, 'arm64-v8a': 8, 'armeabi-v7a': 7, 'x86': 6}
        return f"{lookup.get(distinfo.forkey('archs')[0], 1)}{args.min_sdk_version}{version_code}"
    args.numeric_version = numver() # TODO: Do not abuse args for this.
    if args.intent_filters:
        with open(args.intent_filters) as fd:
            args.intent_filters = fd.read()
    if not args.add_activity:
        args.add_activity = []
    if not args.activity_launch_mode:
        args.activity_launch_mode = ''
    args.extra_source_dirs = []
    service = False
    service_main = join(realpath(args.private), 'service', 'main.py')
    if exists(service_main) or exists(service_main + 'o'):
        service = True
    service_names = []
    for sid, spec in enumerate(args.services):
        spec = spec.split(':')
        name = spec[0]
        entrypoint = spec[1]
        options = spec[2:]
        foreground = 'foreground' in options
        sticky = 'sticky' in options
        service_names.append(name)
        service_target_path =\
            'src/main/java/{}/Service{}.java'.format(
                args.package.replace(".", "/"),
                name.capitalize()
            )
        render(
            'Service.tmpl.java',
            service_target_path,
            name=name,
            entrypoint=entrypoint,
            args=args,
            foreground=foreground,
            sticky=sticky,
            service_id=sid + 1,
        )
    # Find the SDK directory and target API
    with open('project.properties', 'r') as fileh:
        target = fileh.read().strip()
    android_api = target.split('-')[1]
    try:
        int(android_api)
    except (ValueError, TypeError):
        raise ValueError(
            "failed to extract the Android API level from " +
            "build.properties. expected int, got: '" +
            str(android_api) + "'"
        )
    with open('local.properties', 'r') as fileh:
        sdk_dir = fileh.read().strip()
    sdk_dir = sdk_dir[8:]

    # Try to build with the newest available build tools
    ignored = {".DS_Store", ".ds_store"}
    build_tools_versions = [x for x in listdir(join(sdk_dir, 'build-tools')) if x not in ignored]
    build_tools_versions = sorted(build_tools_versions,
                                  key=LooseVersion)
    build_tools_version = build_tools_versions[-1]

    # Folder name for launcher (used by SDL2 bootstrap)
    url_scheme = 'kivy'

    # Render out android manifest:
    manifest_path = "src/main/AndroidManifest.xml"
    render_args = {
        "args": args,
        "service": service,
        "service_names": service_names,
        "android_api": android_api
    }
    if bootstrapname == "sdl2":
        render_args["url_scheme"] = url_scheme
    render(
        'AndroidManifest.tmpl.xml',
        manifest_path,
        **render_args)

    # Copy the AndroidManifest.xml to the dist root dir so that ant
    # can also use it
    if exists('AndroidManifest.xml'):
        remove('AndroidManifest.xml')
    shutil.copy(manifest_path, 'AndroidManifest.xml')
    render(
        'build.tmpl.gradle',
        'build.gradle',
        args = args,
        aars = [],
        jars = [],
        android_api = android_api,
        build_tools_version = build_tools_version,
    )
    render(
        'build.tmpl.xml',
        'build.xml',
        args = args,
        versioned_name = versioned_name,
    )
    render_args = {"args": args, "private_version": str(time.time())}
    if bootstrapname == "sdl2":
        render_args["url_scheme"] = url_scheme
    render('strings.tmpl.xml', res_dir / 'values' / 'strings.xml', **render_args)
    if Path("templates", "custom_rules.tmpl.xml").exists():
        render(
            'custom_rules.tmpl.xml',
            'custom_rules.xml',
            args=args)
    if bootstrapname == "webview":
        render('WebViewLoader.tmpl.java',
               'src/main/java/org/kivy/android/WebViewLoader.java',
               args=args)

    if args.sign:
        render('build.properties', 'build.properties')
    else:
        if exists('build.properties'):
            os.remove('build.properties')
    src_patches = Path('src', 'patches')
    if src_patches.exists():
        log.info("Applying Java source code patches...")
        for patch_name in os.listdir(src_patches):
            patch_path = src_patches / patch_name
            log.info("Applying patch: %s", patch_path)
            try:
                subprocess.check_call(["patch", "-N", "-p1", "-t", "-i", patch_path])
            except subprocess.CalledProcessError as e:
                if e.returncode != 1:
                    raise e
                log.warning("Failed to apply patch (exit code 1), assuming it is already applied: %s", patch_path)
