#!/usr/bin/env python

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

from . import __version__
from .bootstrap import Bootstrap
from .build import Context, build_recipes
from .distribution import Distribution, pretty_log_dists
from .graph import get_recipe_order_and_bootstrap
from .logger import logger, info, warning, setup_color, Out_Style, Out_Fore, info_notify, info_main, shprint
from .recipe import Recipe
from .recommendations import RECOMMENDED_NDK_API, RECOMMENDED_TARGET_API
from .util import BuildInterruptingException, current_directory
from appdirs import user_data_dir
from argparse import ArgumentParser
from distutils.version import LooseVersion
from functools import wraps
from os.path import join, dirname, realpath, exists, expanduser, basename
from sys import platform
import glob, imp, logging, os, re, sh, shlex, shutil, sys # FIXME: Retire imp.

toolchain_dir = dirname(__file__)
sys.path.insert(0, join(toolchain_dir, "tools", "external"))
APK_SUFFIX = '.apk'

def add_boolean_option(parser, names, no_names=None,
                       default=True, dest=None, description=None):
    group = parser.add_argument_group(description=description)
    if not isinstance(names, (list, tuple)):
        names = [names]
    if dest is None:
        dest = names[0].strip("-").replace("-", "_")

    def add_dashes(x):
        return x if x.startswith("-") else "--"+x

    opts = [add_dashes(x) for x in names]
    group.add_argument(
        *opts, help=("(this is the default)" if default else None),
        dest=dest, action='store_true')
    if no_names is None:
        def add_no(x):
            x = x.lstrip("-")
            return ("no_"+x) if "_" in x else ("no-"+x)
        no_names = [add_no(x) for x in names]
    opts = [add_dashes(x) for x in no_names]
    group.add_argument(
        *opts, help=(None if default else "(this is the default)"),
        dest=dest, action='store_false')
    parser.set_defaults(**{dest: default})


def require_prebuilt_dist(func):
    """Decorator for ToolchainCL methods. If present, the method will
    automatically make sure a dist has been built before continuing
    or, if no dists are present or can be obtained, will raise an
    error.
    """

    @wraps(func)
    def wrapper_func(self, args):
        ctx = self.ctx
        ctx.set_archs(self._archs)
        ctx.prepare_build_environment(user_sdk_dir=self.sdk_dir,
                                      user_ndk_dir=self.ndk_dir,
                                      user_android_api=self.android_api,
                                      user_ndk_api=self.ndk_api)
        dist = self._dist
        if dist.needs_build:
            if dist.folder_exists():  # possible if the dist is being replaced
                dist.delete()
            info_notify('No dist exists that meets your requirements, '
                        'so one will be built.')
            build_dist_from_args(ctx, dist, args)
        func(self, args)
    return wrapper_func


def dist_from_args(ctx, args):
    """Parses out any distribution-related arguments, and uses them to
    obtain a Distribution class instance for the build.
    """
    return Distribution.get_distribution(
        ctx,
        name=args.dist_name,
        recipes=split_argument_list(args.requirements),
        arch_name=args.arch,
        ndk_api=args.ndk_api,
        force_build=args.force_build,
        require_perfect_match=args.require_perfect_match,
        allow_replace_dist=args.allow_replace_dist)


def build_dist_from_args(ctx, dist, args):
    """Parses out any bootstrap related arguments, and uses them to build
    a dist."""
    bs = Bootstrap.get_bootstrap(args.bootstrap, ctx)
    blacklist = getattr(args, "blacklist_requirements", "").split(",")
    if len(blacklist) == 1 and blacklist[0] == "":
        blacklist = []
    build_order, python_modules, bs = (
        get_recipe_order_and_bootstrap(
            ctx, dist.recipes, bs,
            blacklist=blacklist
        ))
    assert set(build_order).intersection(set(python_modules)) == set()
    ctx.recipe_build_order = build_order
    ctx.python_modules = python_modules

    info('The selected bootstrap is {}'.format(bs.name))
    info_main('# Creating dist with {} bootstrap'.format(bs.name))
    bs.distribution = dist
    info_notify('Dist will have name {} and requirements ({})'.format(
        dist.name, ', '.join(dist.recipes)))
    info('Dist contains the following requirements as recipes: {}'.format(
        ctx.recipe_build_order))
    info('Dist will also contain modules ({}) installed from pip'.format(
        ', '.join(ctx.python_modules)))

    ctx.distribution = dist
    ctx.prepare_bootstrap(bs)
    if dist.needs_build:
        ctx.prepare_dist()
    build_recipes(build_order, python_modules, ctx, getattr(args, "private", None))
    ctx.bootstrap.run_distribute()

    info_main('# Your distribution was created successfully, exiting.')
    info('Dist can be found at (for now) {}'
         .format(join(ctx.dist_dir, ctx.distribution.dist_dir)))


def split_argument_list(l):
    if not len(l):
        return []
    return re.split(r'[ ,]+', l)

class ToolchainCL:

    def __init__(self):
        parser = ArgumentParser(allow_abbrev = False)
        generic_parser = ArgumentParser(add_help = False)
        generic_parser.add_argument(
            '--debug', dest='debug', action='store_true', default=False,
            help='Display debug output and all build info')
        generic_parser.add_argument(
            '--color', dest='color', choices=['always', 'never', 'auto'],
            help='Enable or disable color output (default enabled on tty)')
        generic_parser.add_argument(
            '--sdk-dir', '--sdk_dir', dest='sdk_dir', default='',
            help='The filepath where the Android SDK is installed')
        generic_parser.add_argument(
            '--ndk-dir', '--ndk_dir', dest='ndk_dir', default='',
            help='The filepath where the Android NDK is installed')
        generic_parser.add_argument(
            '--android-api',
            '--android_api',
            dest='android_api',
            default=0,
            type=int,
            help=('The Android API level to build against defaults to {} if '
                  'not specified.').format(RECOMMENDED_TARGET_API))
        generic_parser.add_argument(
            '--ndk-api', type=int, default=None,
            help=('The Android API level to compile against. This should be your '
                  '*minimal supported* API, not normally the same as your --android-api. '
                  'Defaults to min(ANDROID_API, {}) if not specified.').format(RECOMMENDED_NDK_API))
        generic_parser.add_argument(
            '--symlink-java-src', '--symlink_java_src',
            action='store_true',
            dest='symlink_java_src',
            default=False,
            help=('If True, symlinks the java src folder during build and dist '
                  'creation. This is useful for development only, it could also'
                  ' cause weird problems.'))
        default_storage_dir = user_data_dir('python-for-android')
        if ' ' in default_storage_dir:
            default_storage_dir = '~/.python-for-android'
        generic_parser.add_argument(
            '--storage-dir', dest='storage_dir', default=default_storage_dir,
            help=('Primary storage directory for downloads and builds '
                  '(default: {})'.format(default_storage_dir)))
        generic_parser.add_argument(
            '--arch', help='The arch to build for.',
            default='armeabi-v7a')
        generic_parser.add_argument(
            '--dist-name', '--dist_name',
            help='The name of the distribution to use or create', default='')
        generic_parser.add_argument(
            '--requirements',
            help=('Dependencies of your app, should be recipe names or '
                  'Python modules. NOT NECESSARY if you are using '
                  'Python 3 with --use-setup-py'),
            default='')
        generic_parser.add_argument(
            '--recipe-blacklist',
            help=('Blacklist an internal recipe from use. Allows '
                  'disabling Python 3 core modules to save size'),
            dest="recipe_blacklist",
            default='')
        generic_parser.add_argument(
            '--blacklist-requirements',
            help=('Blacklist an internal recipe from use. Allows '
                  'disabling Python 3 core modules to save size'),
            dest="blacklist_requirements",
            default='')
        generic_parser.add_argument(
            '--bootstrap',
            help='The bootstrap to build with. Leave unset to choose '
                 'automatically.',
            default=None)
        add_boolean_option(
            generic_parser, ["force-build"],
            default=False,
            description='Whether to force compilation of a new distribution')
        add_boolean_option(
            generic_parser, ["require-perfect-match"],
            default=False,
            description=('Whether the dist recipes must perfectly match '
                         'those requested'))
        add_boolean_option(
            generic_parser, ["allow-replace-dist"],
            default=True,
            description='Whether existing dist names can be automatically replaced'
            )
        generic_parser.add_argument(
            '--local-recipes', '--local_recipes',
            dest='local_recipes', default='./p4a-recipes',
            help='Directory to look for local recipes')
        generic_parser.add_argument(
            '--java-build-tool',
            dest='java_build_tool', default='auto',
            choices=['auto', 'ant', 'gradle'],
            help=('The java build tool to use when packaging the APK, defaults '
                  'to automatically selecting an appropriate tool.'))
        add_boolean_option(
            generic_parser, ['copy-libs'],
            default=False,
            description='Copy libraries instead of using biglink (Android 4.3+)'
        )
        self._read_configuration()
        subparsers = parser.add_subparsers(dest = 'subparser_name', help = 'The command to run')
        parser_apk = subparsers.add_parser(
            'apk', help='Build an APK',
            parents=[generic_parser])
        parser_apk.add_argument(
            '--private', dest='private',
            help='the directory with the app source code files' +
                 ' (containing your main.py entrypoint)',
            required=False, default=None)
        parser_apk.add_argument(
            '--release', dest='build_mode', action='store_const',
            const='release', default='debug',
            help='Build the PARSER_APK. in Release mode')
        parser_apk.add_argument(
            '--keystore', dest='keystore', action='store', default=None,
            help=('Keystore for JAR signing key, will use jarsigner '
                  'default if not specified (release build only)'))
        parser_apk.add_argument(
            '--signkey', dest='signkey', action='store', default=None,
            help='Key alias to sign PARSER_APK. with (release build only)')
        parser_apk.add_argument(
            '--keystorepw', dest='keystorepw', action='store', default=None,
            help='Password for keystore')
        parser_apk.add_argument(
            '--signkeypw', dest='signkeypw', action='store', default=None,
            help='Password for key alias')
        subparsers.add_parser(
            'create', help='Compile a set of requirements into a dist',
            parents=[generic_parser])
        subparsers.add_parser(
            'adb', help='Run adb from the given SDK',
            parents=[generic_parser])
        subparsers.add_parser(
            'logcat', help='Run logcat from the given SDK',
            parents=[generic_parser])
        parser.add_argument('-v', '--version', action='version', version=__version__)
        args, unknown = parser.parse_known_args(sys.argv[1:])
        args.unknown_args = unknown
        if hasattr(args, "private") and args.private is not None:
            args.unknown_args += ["--private", args.private]
        self.args = args
        setup_color(args.color)

        if args.debug:
            logger.setLevel(logging.DEBUG)

        self.ctx = Context()
        if hasattr(args, 'requirements'):
            requirements = []
            for requirement in split_argument_list(args.requirements):
                if "==" in requirement:
                    requirement, version = requirement.split(u"==", 1)
                    os.environ["VERSION_{}".format(requirement)] = version
                    info('Recipe {}: version "{}" requested'.format(
                        requirement, version))
                requirements.append(requirement)
            args.requirements = ','.join(requirements)
        self.storage_dir = args.storage_dir
        self.ctx.setup_dirs(self.storage_dir)
        self.sdk_dir = args.sdk_dir
        self.ndk_dir = args.ndk_dir
        self.android_api = args.android_api
        self.ndk_api = args.ndk_api
        self.ctx.symlink_java_src = args.symlink_java_src
        self.ctx.java_build_tool = args.java_build_tool

        self._archs = split_argument_list(args.arch)

        self.ctx.local_recipes = args.local_recipes
        self.ctx.copy_libs = args.copy_libs

        # Each subparser corresponds to a method
        getattr(self, args.subparser_name.replace('-', '_'))(args)

    @property
    def default_storage_dir(self):
        udd = user_data_dir('python-for-android')
        if ' ' in udd:
            udd = '~/.python-for-android'
        return udd

    @staticmethod
    def _read_configuration():
        # search for a .p4a configuration file in the current directory
        if not exists(".p4a"):
            return
        info("Reading .p4a configuration")
        with open(".p4a") as fd:
            lines = fd.readlines()
        lines = [shlex.split(line)
                 for line in lines if not line.startswith("#")]
        for line in lines:
            for arg in line:
                sys.argv.append(arg)

    @property
    def _dist(self):
        ctx = self.ctx
        dist = dist_from_args(ctx, self.args)
        ctx.distribution = dist
        return dist

    @require_prebuilt_dist
    def apk(self, args):
        """Create an APK using the given distribution."""

        ctx = self.ctx
        dist = self._dist

        # Manually fixing these arguments at the string stage is
        # unsatisfactory and should probably be changed somehow, but
        # we can't leave it until later as the build.py scripts assume
        # they are in the current directory.
        fix_args = ('--dir', '--private', '--add-jar', '--add-source',
                    '--whitelist', '--blacklist', '--presplash', '--icon')
        unknown_args = args.unknown_args
        for i, arg in enumerate(unknown_args):
            argx = arg.split('=')
            if argx[0] in fix_args:
                if len(argx) > 1:
                    unknown_args[i] = '='.join(
                        (argx[0], realpath(expanduser(argx[1]))))
                elif i + 1 < len(unknown_args):
                    unknown_args[i+1] = realpath(expanduser(unknown_args[i+1]))

        env = os.environ.copy()
        if args.build_mode == 'release':
            if args.keystore:
                env['P4A_RELEASE_KEYSTORE'] = realpath(expanduser(args.keystore))
            if args.signkey:
                env['P4A_RELEASE_KEYALIAS'] = args.signkey
            if args.keystorepw:
                env['P4A_RELEASE_KEYSTORE_PASSWD'] = args.keystorepw
            if args.signkeypw:
                env['P4A_RELEASE_KEYALIAS_PASSWD'] = args.signkeypw
            elif args.keystorepw and 'P4A_RELEASE_KEYALIAS_PASSWD' not in env:
                env['P4A_RELEASE_KEYALIAS_PASSWD'] = args.keystorepw

        build = imp.load_source('build', join(dist.dist_dir, 'build.py'))
        with current_directory(dist.dist_dir):
            os.environ["ANDROID_API"] = str(self.ctx.android_api)
            build_args = build.parse_args(args.unknown_args)
            build_type = ctx.java_build_tool
            if build_type == 'auto':
                info('Selecting java build tool:')

                build_tools_versions = os.listdir(join(ctx.sdk_dir,
                                                       'build-tools'))
                build_tools_versions = sorted(build_tools_versions,
                                              key=LooseVersion)
                build_tools_version = build_tools_versions[-1]
                info(('Detected highest available build tools '
                      'version to be {}').format(build_tools_version))

                if build_tools_version >= '25.0' and exists('gradlew'):
                    build_type = 'gradle'
                    info('    Building with gradle, as gradle executable is '
                         'present')
                else:
                    build_type = 'ant'
                    if build_tools_version < '25.0':
                        info(('    Building with ant, as the highest '
                              'build-tools-version is only {}').format(
                            build_tools_version))
                    else:
                        info('    Building with ant, as no gradle executable '
                             'detected')

            if build_type == 'gradle':
                # gradle-based build
                env["ANDROID_NDK_HOME"] = self.ctx.ndk_dir
                env["ANDROID_HOME"] = self.ctx.sdk_dir

                gradlew = sh.Command('./gradlew')
                if exists('/usr/bin/dos2unix'):
                    # .../dists/bdisttest_python3/gradlew
                    # .../build/bootstrap_builds/sdl2-python3/gradlew
                    # if docker on windows, gradle contains CRLF
                    output = shprint(
                        sh.Command('dos2unix'), gradlew._path.decode('utf8'),
                        _tail=20, _critical=True, _env=env
                    )
                if args.build_mode == "debug":
                    gradle_task = "assembleDebug"
                elif args.build_mode == "release":
                    gradle_task = "assembleRelease"
                else:
                    raise BuildInterruptingException(
                        "Unknown build mode {} for apk()".format(args.build_mode))
                output = shprint(gradlew, gradle_task, _tail=20,
                                 _critical=True, _env=env)

                # gradle output apks somewhere else
                # and don't have version in file
                apk_dir = join(dist.dist_dir,
                               "build", "outputs", "apk",
                               args.build_mode)
                apk_glob = "*-{}.apk"
                apk_add_version = True

            else:
                # ant-based build
                try:
                    ant = sh.Command('ant')
                except sh.CommandNotFound:
                    raise BuildInterruptingException(
                        'Could not find ant binary, please install it '
                        'and make sure it is in your $PATH.')
                output = shprint(ant, args.build_mode, _tail=20,
                                 _critical=True, _env=env)
                apk_dir = join(dist.dist_dir, "bin")
                apk_glob = "*-*-{}.apk"
                apk_add_version = False
        info_main('# Copying APK to current directory')

        apk_re = re.compile(r'.*Package: (.*\.apk)$')
        apk_file = None
        for line in reversed(output.splitlines()):
            m = apk_re.match(line)
            if m:
                apk_file = m.groups()[0]
                break

        if not apk_file:
            info_main('# APK filename not found in build output. Guessing...')
            if args.build_mode == "release":
                suffixes = ("release", "release-unsigned")
            else:
                suffixes = ("debug", )
            for suffix in suffixes:
                apks = glob.glob(join(apk_dir, apk_glob.format(suffix)))
                if apks:
                    if len(apks) > 1:
                        info('More than one built APK found... guessing you '
                             'just built {}'.format(apks[-1]))
                    apk_file = apks[-1]
                    break
            else:
                raise BuildInterruptingException('Couldn\'t find the built APK')

        info_main('# Found APK file: {}'.format(apk_file))
        if apk_add_version:
            info('# Add version number to APK')
            apk_name = basename(apk_file)[:-len(APK_SUFFIX)]
            apk_file_dest = "{}-{}-{}".format(
                apk_name, build_args.version, APK_SUFFIX)
            info('# APK renamed to {}'.format(apk_file_dest))
            shprint(sh.cp, apk_file, apk_file_dest)
        else:
            shprint(sh.cp, apk_file, './')

    @require_prebuilt_dist
    def create(self, args):
        """Create a distribution directory if it doesn't already exist, run
        any recipes if necessary, and build the apk.
        """
        pass  # The decorator does everything

    def adb(self, args):
        """Runs the adb binary from the detected SDK directory, passing all
        arguments straight to it. This is intended as a convenience
        function if adb is not in your $PATH.
        """
        self._adb(args.unknown_args)

    def logcat(self, args):
        """Runs ``adb logcat`` using the adb binary from the detected SDK
        directory. All extra args are passed as arguments to logcat."""
        self._adb(['logcat'] + args.unknown_args)

    def _adb(self, commands):
        """Call the adb executable from the SDK, passing the given commands as
        arguments."""
        ctx = self.ctx
        ctx.prepare_build_environment(user_sdk_dir=self.sdk_dir,
                                      user_ndk_dir=self.ndk_dir,
                                      user_android_api=self.android_api,
                                      user_ndk_api=self.ndk_api)
        if platform in ('win32', 'cygwin'):
            adb = sh.Command(join(ctx.sdk_dir, 'platform-tools', 'adb.exe'))
        else:
            adb = sh.Command(join(ctx.sdk_dir, 'platform-tools', 'adb'))
        info_notify('Starting adb...')
        output = adb(*commands, _iter=True, _out_bufsize=1, _err_to_out=True)
        for line in output:
            sys.stdout.write(line)
            sys.stdout.flush()

def main():
    ToolchainCL()

if __name__ == "__main__": # TODO: Invoke module directly instead.
    main()
