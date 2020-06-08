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

import json, logging

log = logging.getLogger(__name__)

class Distribution:

    name = None  # A name identifying the dist. May not be None.
    dist_dir = None  # Where the dist dir ultimately is. Should not be None.
    ndk_api = None
    recipes = []

    def __init__(self, ctx):
        self.ctx = ctx # XXX: Is this really needed?

    def __str__(self):
        return '<Distribution: name {} with recipes ({})>'.format(
            # self.name, ', '.join([recipe.name for recipe in self.recipes]))
            self.name, ', '.join(self.recipes))

    def __repr__(self):
        return str(self)

    @classmethod
    def get_distribution(cls, ctx, name, recipes, arch_name, ndk_api):
        possible_dists = []
        if name is not None and name:
            possible_dists = [d for d in possible_dists if d.name == name and arch_name == d.archname]
        _possible_dists = []
        for dist in possible_dists:
            if (
                ndk_api is not None and dist.ndk_api != ndk_api
            ) or dist.ndk_api is None:
                continue
            for recipe in recipes:
                if recipe not in dist.recipes:
                    break
            else:
                _possible_dists.append(dist)
        possible_dists = _possible_dists
        if possible_dists:
            log.info('Of the existing distributions, the following meet the given requirements:')
            for dist in possible_dists:
                log.info("\t%s: min API %s, includes recipes (%s), built for arch (%s)", dist.name, 'unknown' if dist.ndk_api is None else dist.ndk_api, ', '.join(dist.recipes), dist.archname)
        else:
            log.info('No existing dists meet the given requirements!')
        # If any dist has perfect recipes, arch and NDK API, return it
        for dist in possible_dists:
            if ndk_api is not None and dist.ndk_api != ndk_api:
                continue
            if arch_name != dist.archname:
                continue
            if set(recipes).issubset(set(dist.recipes)):
                log.info("%s has compatible recipes, using this one", dist.name)
                return dist
        assert len(possible_dists) < 2
        dist = cls(ctx)
        if not name:
            filen = 'unnamed_dist_{}'
            i = 1
            while (ctx.distsdir / filen.format(i)).exists():
                i += 1
            name = filen.format(i)
        dist.name = name
        dist.dist_dir = ctx.distsdir / f"{name}__{arch_name}"
        dist.recipes = recipes
        dist.ndk_api = ctx.ndk_api
        dist.archname = arch_name
        return dist

    def save_info(self):
        log.info('Saving distribution info')
        with (self.dist_dir / 'dist_info.json').open('w') as f:
            json.dump(dict(
                dist_name = self.name,
                archname = self.ctx.arch.name,
                ndk_api = self.ctx.ndk_api,
                recipes = self.ctx.recipe_build_order + self.ctx.python_modules,
            ), f)
