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
from .build import makeapkversion
from .context import Context, build_recipes
from .distribution import Distribution
from .graph import get_recipe_order
from .logger import setup_color, shprint
from .util import BuildInterruptingException, current_directory
from argparse import ArgumentParser
from distutils.version import LooseVersion
from lagoon import cp
from os.path import join, realpath, expanduser, basename
from pathlib import Path
import glob, logging, os, re, sh

log = logging.getLogger(__name__)

def _createcontext(args):
    ctx = Context()
    ctx.setup_dirs(args.storage_dir)
    ctx.local_recipes = args.local_recipes
    ctx.set_archs(_split_argument_list(args.arch))
    ctx.prepare_build_environment(args.ndk_api)
    return ctx

def _build_dist_from_args(ctx, dist, args):
    bs = Bootstrap.get_bootstrap(args.bootstrap, ctx)
    build_order, python_modules = get_recipe_order(ctx, dist.recipes, bs.recipe_depends, [])
    assert not set(build_order) & set(python_modules)
    ctx.recipe_build_order = build_order
    ctx.python_modules = python_modules
    log.info("The selected bootstrap is %s", bs.name)
    log.info("Creating dist with %s bootstrap", bs.name)
    bs.distribution = dist
    log.info("Dist will have name %s and requirements (%s)", dist.name, ', '.join(dist.recipes))
    log.info("Dist contains the following requirements as recipes: %s", ctx.recipe_build_order)
    log.info("Dist will also contain modules (%s) installed from pip", ', '.join(ctx.python_modules))
    ctx.prepare_bootstrap(bs)
    ctx.prepare_dist()
    build_recipes(build_order, python_modules, ctx)
    ctx.bootstrap.run_distribute()
    log.info('Your distribution was created successfully, exiting.')
    log.info("Dist can be found at (for now) %s", ctx.distsdir / dist.dist_dir)

def _split_argument_list(l):
    return re.split('[ ,]+', l) if l else []

def _require_prebuilt_dist(args, ctx):
    dist = Distribution.get_distribution(
            ctx,
            args.dist_name,
            _split_argument_list(args.requirements),
            args.arch,
            args.ndk_api)
    ctx.distribution = dist
    if dist.needs_build:
        if dist.folder_exists():
            dist.delete()
        log.info('No dist exists that meets your requirements, so one will be built.')
        _build_dist_from_args(ctx, dist, args)
    return dist

def create(args, downstreamargs, ctx, dist):
    pass

def apk(args, downstreamargs, ctx, dist):
    if args.private is not None:
        downstreamargs += ["--private", args.private]
    for i, arg in enumerate(downstreamargs):
        if arg in {'--dir', '--private', '--add-jar', '--add-source', '--whitelist', '--blacklist', '--presplash', '--icon'}:
            downstreamargs[i + 1] = realpath(expanduser(downstreamargs[i + 1]))
    env = os.environ.copy()
    with current_directory(dist.dist_dir):
        apkversion = makeapkversion(downstreamargs, dist.dist_dir)
        log.info('Selecting java build tool:')
        build_tools_versions = os.listdir(join(ctx.sdk_dir, 'build-tools'))
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
            env['ANDROID_NDK_HOME'] = str(ctx.ndk_dir)
            env['ANDROID_HOME'] = str(ctx.sdk_dir)
            gradlew = sh.Command('./gradlew')
            if Path('/usr/bin/dos2unix').exists():
                # .../dists/bdisttest_python3/gradlew
                # .../build/bootstrap_builds/sdl2-python3/gradlew
                # if docker on windows, gradle contains CRLF
                shprint(sh.Command('dos2unix'), gradlew._path.decode('utf8'), _tail=20, _critical=True, _env=env)
            output = shprint(gradlew, dict(debug = 'assembleDebug', release = 'assembleRelease')[args.build_mode], _tail=20, _critical=True, _env=env)
            apk_dir = dist.dist_dir / "build" / "outputs" / "apk" / args.build_mode
            apk_glob = "*-{}.apk"
            apk_add_version = True
        else:
            output = shprint(sh.Command('ant'), args.build_mode, _tail=20, _critical=True, _env=env)
            apk_dir = dist.dist_dir / "bin"
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
        APK_SUFFIX = '.apk'
        apk_name = basename(apk_file)[:-len(APK_SUFFIX)]
        apk_file_dest = f"{apk_name}-{apkversion}-{APK_SUFFIX}" # XXX: This looks wrong?
        log.info("APK renamed to %s", apk_file_dest)
        cp.print(apk_file, apk_file_dest)
    else:
        cp.print(apk_file, './')

def main():
    setup_color(True)
    commonparser = ArgumentParser(add_help = False)
    commonparser.add_argument('--ndk-api', type = int)
    commonparser.add_argument('--storage-dir', type = lambda p: Path(p).expanduser())
    commonparser.add_argument('--arch', default = 'armeabi-v7a')
    commonparser.add_argument('--dist-name')
    commonparser.add_argument('--requirements', default = '')
    commonparser.add_argument('--bootstrap')
    commonparser.add_argument('--local-recipes')
    parser = ArgumentParser(allow_abbrev = False)
    subparsers = parser.add_subparsers(dest = 'command')
    subparsers.add_parser('create', parents = [commonparser])
    apkparser = subparsers.add_parser('apk', parents = [commonparser])
    apkparser.add_argument('--private')
    apkparser.add_argument('--release', dest = 'build_mode', action = 'store_const', const = 'release', default = 'debug')
    args, downstreamargs = parser.parse_known_args()
    ctx = _createcontext(args)
    globals()[args.command](args, downstreamargs, ctx, _require_prebuilt_dist(args, ctx))

if __name__ == "__main__": # TODO: Invoke module directly instead.
    main()
