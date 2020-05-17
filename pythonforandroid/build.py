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

from argparse import ArgumentParser
from distutils.version import LooseVersion
from fnmatch import fnmatch
from os import listdir, makedirs, remove
from os.path import dirname, join, isfile, realpath, relpath, split, exists, basename
from pathlib import Path
from zipfile import ZipFile
import jinja2, json, logging, os, shutil, subprocess, tarfile, tempfile, time

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
    if exists(fn):
        os.unlink(fn)

def _ensure_dir(path):
    if not exists(path):
        makedirs(path)

class Render:

    def __init__(self, common_build):
        self.environment = jinja2.Environment(loader = jinja2.FileSystemLoader(common_build / 'templates'))

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

def _make_python_zip(blacklist):
    if not exists('private'):
        log.info('No compiled python is present to zip, skipping.')
        return []
    d = realpath(join('private', 'lib', 'python2.7'))
    def select(fn):
        if blacklist.has(fn):
            return False
        fn = realpath(fn)
        assert(fn.startswith(d))
        fn = fn[len(d):]
        if (fn.startswith('/site-packages/')
                or fn.startswith('/config/')
                or fn.startswith('/lib-dynload/')
                or fn.startswith('/libpymodules.so')):
            return False
        return fn
    python_files = [x for x in _listfiles(d) if select(x)]
    zfn = join('private', 'lib', 'python27.zip')
    zf = ZipFile(zfn, 'w')
    for fn in python_files:
        zf.write(fn, fn[len(d):])
    zf.close()
    return python_files

def _make_tar(tfn, source_dirs, optimize_python, blacklist, distinfo, python_files):
    def select(fn):
        rfn = realpath(fn)
        return False if rfn in python_files else not blacklist.has(fn)
    files = []
    for sd in source_dirs:
        sd = realpath(sd)
        _compile_dir(sd, optimize_python, distinfo)
        files.extend([x, relpath(realpath(x), sd)] for x in _listfiles(sd) if select(x))
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

def _compile_dir(dfn, optimize_python, distinfo):
    args = [distinfo.forkey('hostpython'), '-m', 'compileall', '-b', '-f', dfn]
    if optimize_python:
        args.insert(1, '-OO')
    subprocess.check_call(args)

def _make_package(args, bootstrapname, blacklist, distinfo, render):
    if (bootstrapname != "sdl" or args.launcher is None) and bootstrapname != "webview":
        if args.private is None or (
                not exists(join(realpath(args.private), 'main.py')) and
                not exists(join(realpath(args.private), 'main.pyo'))):
            raise Exception('No main.py(o) found in your app directory. This file must exist to act as the entry point for you app. If your app is started by a file with a different name, rename it to main.py or add a main.py that loads it.')
    assets_dir = Path('src', 'main', 'assets')
    _try_unlink(assets_dir / 'public.mp3')
    _try_unlink(assets_dir / 'private.mp3')
    _ensure_dir(assets_dir)
    python_files = _make_python_zip(blacklist)
    env_vars_tarpath = tempfile.mkdtemp(prefix = "p4a-extra-env-")
    with Path(env_vars_tarpath, "p4a_env_vars.txt").open("w") as f:
        if hasattr(args, "window"):
            f.write("P4A_IS_WINDOWED=" + str(args.window) + "\n")
        if hasattr(args, "orientation"):
            f.write("P4A_ORIENTATION=" + str(args.orientation) + "\n")
        f.write("P4A_NUMERIC_VERSION=" + str(args.numeric_version) + "\n")
        f.write("P4A_MINSDK=" + str(args.min_sdk_version) + "\n")
    tar_dirs = [env_vars_tarpath]
    if args.private:
        log.info('No setup.py/pyproject.toml used, copying full private data into .apk.')
        tar_dirs.append(args.private)
    for python_bundle_dir in 'private', '_python_bundle':
        if exists(python_bundle_dir):
            tar_dirs.append(python_bundle_dir)
    if bootstrapname == "webview":
        tar_dirs.append('webview_includes')
    if args.private or args.launcher:
        _make_tar(assets_dir / 'private.mp3', tar_dirs, args.optimize_python, blacklist, distinfo, python_files)
    shutil.rmtree(env_vars_tarpath)
    res_dir = Path('src', 'main', 'res')
    default_icon = 'templates/kivy-icon.png'
    default_presplash = 'templates/kivy-presplash.jpg'
    shutil.copy(args.icon or default_icon, res_dir / 'drawable' / 'icon.png')
    if bootstrapname != "service_only":
        shutil.copy(args.presplash or default_presplash, res_dir / 'drawable' / 'presplash.jpg')
    jars = []
    if args.add_jar:
        for jarname in args.add_jar:
            if not exists(jarname):
                raise Exception("Requested jar does not exist: %s" % jarname)
            shutil.copy(jarname, 'src/main/libs')
            jars.append(basename(jarname))
    aars = []
    if args.add_aar:
        _ensure_dir("libs")
        for aarname in args.add_aar:
            if not exists(aarname):
                raise Exception("Requested aar does not exists: %s" % aarname)
            shutil.copy(aarname, 'libs')
            aars.append(basename(aarname).rsplit('.', 1)[0])

    versioned_name = (args.name.replace(' ', '').replace('\'', '') +
                      '-' + args.version)

    version_code = 0
    if not args.numeric_version:
        # Set version code in format (arch-minsdk-app_version)
        arch = distinfo.forkey("archs")[0]
        arch_dict = {"x86_64": "9", "arm64-v8a": "8", "armeabi-v7a": "7", "x86": "6"}
        arch_code = arch_dict.get(arch, '1')
        min_sdk = args.min_sdk_version
        for i in args.version.split('.'):
            version_code *= 100
            version_code += int(i)
        args.numeric_version = "{}{}{}".format(arch_code, min_sdk, version_code)

    if args.intent_filters:
        with open(args.intent_filters) as fd:
            args.intent_filters = fd.read()

    if not args.add_activity:
        args.add_activity = []

    if not args.activity_launch_mode:
        args.activity_launch_mode = ''

    if args.extra_source_dirs:
        esd = []
        for spec in args.extra_source_dirs:
            if ':' in spec:
                specdir, specincludes = spec.split(':')
            else:
                specdir = spec
                specincludes = '**'
            esd.append((realpath(specdir), specincludes))
        args.extra_source_dirs = esd
    else:
        args.extra_source_dirs = []

    service = False
    if args.private:
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

    # gradle build templates
    render(
        'build.tmpl.gradle',
        'build.gradle',
        args=args,
        aars=aars,
        jars=jars,
        android_api=android_api,
        build_tools_version=build_tools_version
        )

    # ant build templates
    render(
        'build.tmpl.xml',
        'build.xml',
        args=args,
        versioned_name=versioned_name)

    # String resources:
    render_args = {
        "args": args,
        "private_version": str(time.time())
    }
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

def makeapkversion(args, distdir, common_build):
    render = Render(common_build)
    distinfo = DistInfo(distdir)
    ndk_api = default_min_api = int(distinfo.forkey('ndk_api'))
    bootstrapname = distinfo.forkey('bootstrap')
    blacklist = Blacklist(bootstrapname)
    ap = ArgumentParser()
    ap.add_argument('--private', required = bootstrapname != "sdl2")
    ap.add_argument('--package', dest='package',
                    help=('The name of the java package the project will be'
                          ' packaged under.'),
                    required=True)
    ap.add_argument('--name', dest='name',
                    help=('The human-readable name of the project.'),
                    required=True)
    ap.add_argument('--numeric-version', dest='numeric_version',
                    help=('The numeric version number of the project. If not '
                          'given, this is automatically computed from the '
                          'version.'))
    ap.add_argument('--version', dest='version',
                    help=('The version number of the project. This should '
                          'consist of numbers and dots, and should have the '
                          'same number of groups of numbers as previous '
                          'versions.'),
                    required=True)
    if bootstrapname == "sdl2":
        ap.add_argument('--launcher', dest='launcher', action='store_true',
                        help=('Provide this argument to build a multi-app '
                              'launcher, rather than a single app.'))
    ap.add_argument('--permission', dest='permissions', action='append', default=[],
                    help='The permissions to give this app.', nargs='+')
    ap.add_argument('--meta-data', dest='meta_data', action='append', default=[],
                    help='Custom key=value to add in application metadata')
    ap.add_argument('--uses-library', dest='android_used_libs', action='append', default=[],
                    help='Used shared libraries included using <uses-library> tag in AndroidManifest.xml')
    ap.add_argument('--icon', dest='icon',
                    help=('A png file to use as the icon for '
                          'the application.'))
    ap.add_argument('--service', dest='services', action='append', default=[],
                    help='Declare a new service entrypoint: '
                         'NAME:PATH_TO_PY[:foreground]')
    if bootstrapname != "service_only":
        ap.add_argument('--presplash', dest='presplash',
                        help=('A jpeg file to use as a screen while the '
                              'application is loading.'))
        ap.add_argument('--presplash-color',
                        dest='presplash_color',
                        default='#000000',
                        help=('A string to set the loading screen '
                              'background color. '
                              'Supported formats are: '
                              '#RRGGBB #AARRGGBB or color names '
                              'like red, green, blue, etc.'))
        ap.add_argument('--window', dest='window', action='store_true',
                        default=False,
                        help='Indicate if the application will be windowed')
        ap.add_argument('--orientation', dest='orientation',
                        default='portrait',
                        help=('The orientation that the game will '
                              'display in. '
                              'Usually one of "landscape", "portrait", '
                              '"sensor", or "user" (the same as "sensor" '
                              'but obeying the '
                              'user\'s Android rotation setting). '
                              'The full list of options is given under '
                              'android_screenOrientation at '
                              'https://developer.android.com/guide/'
                              'topics/manifest/'
                              'activity-element.html'))

    ap.add_argument('--android-entrypoint', dest='android_entrypoint',
                    default='org.kivy.android.PythonActivity',
                    help='Defines which java class will be used for startup, usually a subclass of PythonActivity')
    ap.add_argument('--android-apptheme', dest='android_apptheme',
                    default='@android:style/Theme.NoTitleBar',
                    help='Defines which app theme should be selected for the main activity')
    ap.add_argument('--add-compile-option', dest='compile_options', default=[],
                    action='append', help='add compile options to gradle.build')
    ap.add_argument('--add-gradle-repository', dest='gradle_repositories',
                    default=[],
                    action='append',
                    help='Ddd a repository for gradle')
    ap.add_argument('--add-packaging-option', dest='packaging_options',
                    default=[],
                    action='append',
                    help='Dndroid packaging options')

    ap.add_argument('--wakelock', dest='wakelock', action='store_true',
                    help=('Indicate if the application needs the device '
                          'to stay on'))
    ap.add_argument('--blacklist', dest='blacklist',
                    default = distdir / 'blacklist.txt',
                    help=('Use a blacklist file to match unwanted file in '
                          'the final APK'))
    ap.add_argument('--whitelist', dest='whitelist',
                    default = distdir / 'whitelist.txt',
                    help=('Use a whitelist file to prevent blacklisting of '
                          'file in the final APK'))
    ap.add_argument('--add-jar', dest='add_jar', action='append',
                    help=('Add a Java .jar to the libs, so you can access its '
                          'classes with pyjnius. You can specify this '
                          'argument more than once to include multiple jars'))
    ap.add_argument('--add-aar', dest='add_aar', action='append',
                    help=('Add an aar dependency manually'))
    ap.add_argument('--depend', dest='depends', action='append',
                    help=('Add a external dependency '
                          '(eg: com.android.support:appcompat-v7:19.0.1)'))
    # The --sdk option has been removed, it is ignored in favour of
    # --android-api handled by toolchain.py
    ap.add_argument('--sdk', dest='sdk_version', default=-1,
                    type=int, help=('Deprecated argument, does nothing'))
    ap.add_argument('--minsdk', dest='min_sdk_version',
                    default=default_min_api, type=int,
                    help=('Minimum Android SDK version that the app supports. '
                          'Defaults to {}.'.format(default_min_api)))
    ap.add_argument('--allow-minsdk-ndkapi-mismatch', default=False,
                    action='store_true',
                    help=('Allow the --minsdk argument to be different from '
                          'the discovered ndk_api in the dist'))
    ap.add_argument('--intent-filters', dest='intent_filters',
                    help=('Add intent-filters xml rules to the '
                          'AndroidManifest.xml file. The argument is a '
                          'filename containing xml. The filename should be '
                          'located relative to the python-for-android '
                          'directory'))
    ap.add_argument('--with-billing', dest='billing_pubkey',
                    help='If set, the billing service will be added (not implemented)')
    ap.add_argument('--add-source', dest='extra_source_dirs', action='append',
                    help='Include additional source dirs in Java build')
    if bootstrapname == "webview":
        ap.add_argument('--port',
                        help='The port on localhost that the WebView will access',
                        default='5000')
    ap.add_argument('--sign', action='store_true',
                    help=('Try to sign the APK with your credentials. You must set '
                          'the appropriate environment variables.'))
    ap.add_argument('--add-activity', dest='add_activity', action='append',
                    help='Add this Java class as an Activity to the manifest.')
    ap.add_argument('--activity-launch-mode',
                    dest='activity_launch_mode',
                    default='singleTask',
                    help='Set the launch mode of the main activity in the manifest.')
    ap.add_argument('--allow-backup', dest='allow_backup', default='true',
                    help="if set to 'false', then android won't backup the application.")
    ap.add_argument('--no-optimize-python', dest='optimize_python',
                    action='store_false', default=True,
                    help=('Whether to compile to optimised .pyo files, using -OO '
                          '(strips docstrings and asserts)'))
    ap.add_argument('--extra-manifest-xml', default='',
                    help=('Extra xml to write directly inside the <manifest> element of'
                          'AndroidManifest.xml'))
    args = ap.parse_args(args)
    if args.name and args.name[0] == '"' and args.name[-1] == '"':
        args.name = args.name[1:-1]

    if ndk_api != args.min_sdk_version:
        log.warning("--minsdk argument does not match the api that is compiled against. Only proceed if you know what you are doing, otherwise use --minsdk=%s or recompile against api %s", ndk_api, args.min_sdk_version)
        if not args.allow_minsdk_ndkapi_mismatch:
            raise Exception('You must pass --allow-minsdk-ndkapi-mismatch to build with --minsdk different to the target NDK api from the build step')
        log.info('Proceeding with --minsdk not matching build target api')
    if args.billing_pubkey:
        raise Exception('Billing not yet supported!')
    if args.sdk_version == -1:
        log.warning('WARNING: Received a --sdk argument, but this argument is deprecated and does nothing.')
        args.sdk_version = -1  # ensure it is not used

    if args.permissions and isinstance(args.permissions[0], list):
        args.permissions = [p for perm in args.permissions for p in perm]
    if args.blacklist:
        with open(args.blacklist) as fd:
            patterns = [x.strip() for x in fd.read().splitlines()
                        if x.strip() and not x.strip().startswith('#')]
        blacklist.BLACKLIST_PATTERNS += patterns
    if args.whitelist:
        with open(args.whitelist) as fd:
            patterns = [x.strip() for x in fd.read().splitlines()
                        if x.strip() and not x.strip().startswith('#')]
        blacklist.WHITELIST_PATTERNS += patterns
    if args.private is None and bootstrapname == 'sdl2' and args.launcher is None:
        raise Exception('Need --private directory or --launcher (SDL2 bootstrap only)to have something to launch inside the .apk!')
    _make_package(args, bootstrapname, blacklist, distinfo, render)
    return args.version