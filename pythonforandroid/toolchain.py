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

from .bootstrap import Bootstrap
from .build import Context, build_recipes
from .distribution import Distribution
from .graph import get_recipe_order_and_bootstrap
from .logger import logger, setup_color, shprint
from .recommendations import RECOMMENDED_NDK_API
from .util import BuildInterruptingException, current_directory
from appdirs import user_data_dir
from distutils.version import LooseVersion
from lagoon import cp
from os.path import join, dirname, realpath, expanduser, basename
from pathlib import Path
import argparse, glob, imp, logging, os, re, sh, sys # FIXME: Retire imp.

log = logging.getLogger(__name__)
toolchain_dir = dirname(__file__)
sys.path.insert(0, join(toolchain_dir, "tools", "external"))
APK_SUFFIX = '.apk'

class ArgumentParser(argparse.ArgumentParser):

    def add_boolean_option(self, name, default, description):
        group = self.add_argument_group(description = description)
        dest = name.replace('-', '_')
        group.add_argument(f"--{name}",
                help = "(this is the default)" if default else None, dest = dest, action = 'store_true')
        group.add_argument(f"--no-{name}",
                help = None if default else "(this is the default)", dest = dest, action = 'store_false')
        self.set_defaults(**{dest: default})

def _dist_from_args(ctx, args):
    return Distribution.get_distribution(
        ctx,
        name=args.dist_name,
        recipes=_split_argument_list(args.requirements),
        arch_name=args.arch,
        ndk_api=args.ndk_api,
        force_build=args.force_build,
        require_perfect_match=args.require_perfect_match,
        allow_replace_dist=args.allow_replace_dist)

def _build_dist_from_args(ctx, dist, args):
    bs = Bootstrap.get_bootstrap(args.bootstrap, ctx)
    blacklist = getattr(args, "blacklist_requirements", "").split(",")
    if len(blacklist) == 1 and blacklist[0] == "":
        blacklist = []
    build_order, python_modules, bs = get_recipe_order_and_bootstrap(ctx, dist.recipes, bs, blacklist = blacklist)
    assert not set(build_order) & set(python_modules)
    ctx.recipe_build_order = build_order
    ctx.python_modules = python_modules
    log.info("The selected bootstrap is %s", bs.name)
    log.info("Creating dist with %s bootstrap", bs.name)
    bs.distribution = dist
    log.info("Dist will have name %s and requirements (%s)", dist.name, ', '.join(dist.recipes))
    log.info("Dist contains the following requirements as recipes: %s", ctx.recipe_build_order)
    log.info("Dist will also contain modules (%s) installed from pip", ', '.join(ctx.python_modules))
    ctx.distribution = dist
    ctx.prepare_bootstrap(bs)
    if dist.needs_build:
        ctx.prepare_dist()
    build_recipes(build_order, python_modules, ctx, getattr(args, "private", None))
    ctx.bootstrap.run_distribute()
    log.info('Your distribution was created successfully, exiting.')
    log.info("Dist can be found at (for now) %s", join(ctx.dist_dir, dist.dist_dir))

def _split_argument_list(l):
    return re.split('[ ,]+', l) if l else []

class ToolchainCL:

    def __init__(self):
        generic_parser = ArgumentParser(add_help = False)
        generic_parser.add_argument(
            '--debug', dest='debug', action='store_true', default=False,
            help='Display debug output and all build info')
        generic_parser.add_argument(
            '--color', dest='color', choices=['always', 'never', 'auto'],
            help='Enable or disable color output (default enabled on tty)')
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
        generic_parser.add_boolean_option('force-build', False, 'Whether to force compilation of a new distribution')
        generic_parser.add_boolean_option('require-perfect-match', False, 'Whether the dist recipes must perfectly match those requested')
        generic_parser.add_boolean_option('allow-replace-dist', True, 'Whether existing dist names can be automatically replaced')
        generic_parser.add_argument(
            '--local-recipes', '--local_recipes',
            dest='local_recipes', default='./p4a-recipes',
            help='Directory to look for local recipes')
        generic_parser.add_boolean_option('copy-libs', False, 'Copy libraries instead of using biglink (Android 4.3+)')
        parser = ArgumentParser(allow_abbrev = False)
        subparsers = parser.add_subparsers(dest = 'command')
        subparsers.add_parser('create', parents = [generic_parser])
        parser_apk = subparsers.add_parser('apk', parents = [generic_parser])
        parser_apk.add_argument('--private')
        parser_apk.add_argument('--release', dest = 'build_mode', action = 'store_const', const = 'release', default = 'debug')
        parser_apk.add_argument('--keystore')
        parser_apk.add_argument('--signkey')
        parser_apk.add_argument('--keystorepw')
        parser_apk.add_argument('--signkeypw')
        args, unknown = parser.parse_known_args()
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
            for requirement in _split_argument_list(args.requirements):
                if "==" in requirement:
                    requirement, version = requirement.split(u"==", 1)
                    os.environ["VERSION_{}".format(requirement)] = version
                    log.info("""Recipe %s: version "%s" requested""", requirement, version)
                requirements.append(requirement)
            args.requirements = ','.join(requirements)
        self.storage_dir = args.storage_dir
        self.ctx.setup_dirs(self.storage_dir)
        self.ctx.symlink_java_src = args.symlink_java_src
        self._archs = _split_argument_list(args.arch)
        self.ctx.local_recipes = args.local_recipes
        self.ctx.copy_libs = args.copy_libs
        getattr(self, args.command)(args, self._require_prebuilt_dist(args))

    @property
    def default_storage_dir(self):
        udd = user_data_dir('python-for-android')
        if ' ' in udd:
            udd = '~/.python-for-android'
        return udd

    def _require_prebuilt_dist(self, args):
        self.ctx.set_archs(self._archs)
        self.ctx.prepare_build_environment(args.ndk_api)
        dist = _dist_from_args(self.ctx, args)
        self.ctx.distribution = dist
        if dist.needs_build:
            if dist.folder_exists():
                dist.delete()
            log.info('No dist exists that meets your requirements, so one will be built.')
            _build_dist_from_args(self.ctx, dist, args)
        return dist

    def create(self, args, dist):
        pass

    def apk(self, args, dist):
        fix_args = '--dir', '--private', '--add-jar', '--add-source', '--whitelist', '--blacklist', '--presplash', '--icon'
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
            log.info('Selecting java build tool:')
            build_tools_versions = os.listdir(join(self.ctx.sdk_dir, 'build-tools'))
            build_tools_versions = sorted(build_tools_versions, key = LooseVersion)
            build_tools_version = build_tools_versions[-1]
            log.info("Detected highest available build tools version to be %s", build_tools_version)
            if build_tools_version >= '25.0' and Path('gradlew').exists(): # TODO: Retire gradlew.
                build_type = 'gradle'
                log.info('    Building with gradle, as gradle executable is present')
            else:
                build_type = 'ant'
                if build_tools_version < '25.0':
                    log.info("    Building with ant, as the highest build-tools-version is only %s", build_tools_version)
                else:
                    log.info('    Building with ant, as no gradle executable detected')
            if build_type == 'gradle':
                env['ANDROID_NDK_HOME'] = str(self.ctx.ndk_dir)
                env['ANDROID_HOME'] = str(self.ctx.sdk_dir)
                gradlew = sh.Command('./gradlew')
                if Path('/usr/bin/dos2unix').exists():
                    # .../dists/bdisttest_python3/gradlew
                    # .../build/bootstrap_builds/sdl2-python3/gradlew
                    # if docker on windows, gradle contains CRLF
                    shprint(sh.Command('dos2unix'), gradlew._path.decode('utf8'), _tail=20, _critical=True, _env=env)
                output = shprint(gradlew, dict(debug = 'assembleDebug', release = 'assembleRelease')[args.build_mode], _tail=20, _critical=True, _env=env)
                apk_dir = join(dist.dist_dir, "build", "outputs", "apk", args.build_mode)
                apk_glob = "*-{}.apk"
                apk_add_version = True
            else:
                output = shprint(sh.Command('ant'), args.build_mode, _tail=20, _critical=True, _env=env)
                apk_dir = join(dist.dist_dir, "bin")
                apk_glob = "*-*-{}.apk"
                apk_add_version = False
        log.info('Copying APK to current directory')
        apk_re = re.compile(r'.*Package: (.*\.apk)$')
        apk_file = None
        for line in reversed(output.splitlines()):
            m = apk_re.match(line)
            if m:
                apk_file = m.groups()[0]
                break
        if not apk_file:
            log.info('APK filename not found in build output. Guessing...')
            if args.build_mode == "release":
                suffixes = ("release", "release-unsigned")
            else:
                suffixes = ("debug", )
            for suffix in suffixes:
                apks = glob.glob(join(apk_dir, apk_glob.format(suffix)))
                if apks:
                    if len(apks) > 1:
                        log.info("More than one built APK found... guessing you just built %s", apks[-1])
                    apk_file = apks[-1]
                    break
            else:
                raise BuildInterruptingException('Couldn\'t find the built APK')
        log.info("Found APK file: %s", apk_file)
        if apk_add_version:
            log.info('Add version number to APK')
            apk_name = basename(apk_file)[:-len(APK_SUFFIX)]
            apk_file_dest = "{}-{}-{}".format(
                apk_name, build_args.version, APK_SUFFIX)
            log.info("APK renamed to %s", apk_file_dest)
            cp.print(apk_file, apk_file_dest)
        else:
            cp.print(apk_file, './')

def main():
    ToolchainCL()

if __name__ == "__main__": # TODO: Invoke module directly instead.
    main()
