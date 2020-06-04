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
from .distribution import Distribution
from .graph import get_recipe_order
from lagoon import gradle
from p4a.boot import Bootstrap
import logging

log = logging.getLogger(__name__)

def _build_dist_from_args(ctx, dist, bootstrap):
    bs = Bootstrap.get_bootstrap(bootstrap, ctx)
    build_order, python_modules = get_recipe_order(ctx, dist.recipes, bs.recipe_depends, ['genericndkbuild', 'python2'])
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
    ctx.build_recipes(build_order, python_modules)
    ctx.bootstrap.run_distribute()
    log.info('Your distribution was created successfully, exiting.')
    log.info("Dist can be found at (for now) %s", ctx.distsdir / dist.dist_dir)

def create(ctx, dist_name, bootstrap, arch, ndk_api, requirements):
    dist = Distribution.get_distribution(
            ctx,
            dist_name,
            requirements,
            arch,
            ndk_api)
    ctx.distribution = dist
    if dist.needs_build:
        if dist.folder_exists():
            dist.delete()
        log.info('No dist exists that meets your requirements, so one will be built.')
        _build_dist_from_args(ctx, dist, bootstrap)
    return dist

def makeapk(ctx, dist, app_dir, release, downstreamargs):
    build_mode = 'release' if release else 'debug'
    makeapkversion(downstreamargs, dist.dist_dir, app_dir)
    env = dict(ANDROID_NDK_HOME = ctx.ndk_dir, ANDROID_HOME = ctx.sdk_dir)
    gradle.__no_daemon.print(dict(debug = 'assembleDebug', release = 'assembleRelease')[build_mode], env = env, cwd = dist.dist_dir)
