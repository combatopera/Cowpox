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

from .build import makeapkversion
from .context import Context, build_recipes
from .graph import get_recipe_order
from lagoon import cp, gradle
from pathlib import Path
from pythonforandroid.bootstrap import Bootstrap
from pythonforandroid.distribution import Distribution
from pythonforandroid.util import BuildInterruptingException, current_directory
from types import SimpleNamespace
import glob, logging, os, re

log = logging.getLogger(__name__)

def _createcontext(args, sdkpath, apilevel, ndkpath):
    ctx = Context()
    ctx.setup_dirs(args.storage_dir)
    ctx.local_recipes = args.local_recipes
    ctx.set_archs([args.arch])
    ctx.prepare_build_environment(args.ndk_api, sdkpath, apilevel, ndkpath)
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
            args.requirements,
            args.arch,
            args.ndk_api)
    ctx.distribution = dist
    if dist.needs_build:
        if dist.folder_exists():
            dist.delete()
        log.info('No dist exists that meets your requirements, so one will be built.')
        _build_dist_from_args(ctx, dist, args)
    return dist

def apk(args, downstreamargs, ctx, dist):
    with current_directory(dist.dist_dir):
        apkversion = makeapkversion(downstreamargs, dist.dist_dir, args.private.expanduser().resolve())
        env = os.environ.copy()
        env['ANDROID_NDK_HOME'] = str(ctx.ndk_dir)
        env['ANDROID_HOME'] = str(ctx.sdk_dir)
        output = gradle.tee(dict(debug = 'assembleDebug', release = 'assembleRelease')[args.build_mode], env = env)
        apk_dir = dist.dist_dir / "build" / "outputs" / "apk" / args.build_mode
        apk_glob = "*-{}.apk"
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
            apks = glob.glob(str(apk_dir / apk_glob.format(suffix)))
            if apks:
                if len(apks) > 1:
                    log.info("More than one built APK found... guessing you just built %s", apks[-1])
                apk_file = apks[-1]
                break
        else:
            raise BuildInterruptingException('Couldn\'t find the built APK')
    log.info("Found APK file: %s", apk_file)
    log.info('Add version number to APK')
    APK_SUFFIX = '.apk'
    apk_name = Path(apk_file).name[:-len(APK_SUFFIX)]
    apk_file_dest = f"{apk_name}-{apkversion}-{APK_SUFFIX}" # XXX: This looks wrong?
    log.info("APK renamed to %s", apk_file_dest)
    cp.print(apk_file, apk_file_dest)

def create(sdkpath, ndkpath, apilevel, dist_name, bootstrap, arch, storage_dir, ndk_api, local_recipes, requirements):
    args = SimpleNamespace(
        dist_name = dist_name,
        bootstrap = bootstrap,
        arch = arch,
        storage_dir = storage_dir,
        ndk_api = ndk_api,
        local_recipes = local_recipes,
        requirements = requirements,
    )
    ctx = _createcontext(args, sdkpath, apilevel, ndkpath)
    _require_prebuilt_dist(args, ctx)

def makeapk(sdkpath, ndkpath, apilevel, dist_name, bootstrap, arch, storage_dir, ndk_api, local_recipes, private, release, downstreamargs):
    args = SimpleNamespace(
        dist_name = dist_name,
        bootstrap = bootstrap,
        arch = arch,
        storage_dir = storage_dir,
        ndk_api = ndk_api,
        local_recipes = local_recipes,
        requirements = [],
        private = private,
        build_mode = 'release' if release else 'debug',
    )
    ctx = _createcontext(args, sdkpath, apilevel, ndkpath)
    apk(args, downstreamargs, ctx, _require_prebuilt_dist(args, ctx))