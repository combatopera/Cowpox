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

from .logger import info, info_notify, warning, Err_Style, Err_Fore
from .util import current_directory
from os.path import exists, join
from pathlib import Path
import glob, json, shutil

class Distribution:
    '''State container for information about a distribution (i.e. an
    Android project).

    This is separate from a Bootstrap because the Bootstrap is
    concerned with building and populating the dist directory, whereas
    the dist itself could also come from e.g. a binary download.
    '''
    ctx = None

    name = None  # A name identifying the dist. May not be None.
    needs_build = False  # Whether the dist needs compiling
    url = None
    dist_dir = None  # Where the dist dir ultimately is. Should not be None.
    ndk_api = None

    archs = []
    '''The names of the arch targets that the dist is built for.'''

    recipes = []

    description = ''  # A long description

    def __init__(self, ctx):
        self.ctx = ctx

    def __str__(self):
        return '<Distribution: name {} with recipes ({})>'.format(
            # self.name, ', '.join([recipe.name for recipe in self.recipes]))
            self.name, ', '.join(self.recipes))

    def __repr__(self):
        return str(self)

    @classmethod
    def get_distribution(cls, ctx, name, recipes, arch_name, ndk_api):
        possible_dists = cls._get_distributions(ctx)
        if name is not None and name:
            possible_dists = [d for d in possible_dists if (d.name == name) and (arch_name in d.archs)]
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
            info('Of the existing distributions, the following meet the given requirements:')
            _pretty_log_dists(possible_dists)
        else:
            info('No existing dists meet the given requirements!')
        # If any dist has perfect recipes, arch and NDK API, return it
        for dist in possible_dists:
            if ndk_api is not None and dist.ndk_api != ndk_api:
                continue
            if arch_name is not None and arch_name not in dist.archs:
                continue
            if set(recipes).issubset(set(dist.recipes)):
                info_notify('{} has compatible recipes, using this one'.format(dist.name))
                return dist
        assert len(possible_dists) < 2
        dist = cls(ctx)
        dist.needs_build = True
        if not name:
            filen = 'unnamed_dist_{}'
            i = 1
            while (ctx.distsdir / filen.format(i)).exists():
                i += 1
            name = filen.format(i)
        dist.name = name
        dist.dist_dir = ctx.distsdir / generate_dist_folder_name(name, None if arch_name is None else [arch_name])
        dist.recipes = recipes
        dist.ndk_api = ctx.ndk_api
        dist.archs = [arch_name]
        return dist

    def folder_exists(self):
        return self.dist_dir.exists()

    def delete(self):
        shutil.rmtree(self.dist_dir)

    @classmethod
    def _get_distributions(cls, ctx):
        folders = glob.glob(str(ctx.distsdir / '*'))
        dists = []
        for folder in folders:
            if exists(join(folder, 'dist_info.json')):
                with open(join(folder, 'dist_info.json')) as fileh:
                    dist_info = json.load(fileh)
                dist = cls(ctx)
                dist.name = dist_info['dist_name']
                dist.dist_dir = Path(folder)
                dist.needs_build = False
                dist.recipes = dist_info['recipes']
                if 'archs' in dist_info:
                    dist.archs = dist_info['archs']
                if 'ndk_api' in dist_info:
                    dist.ndk_api = dist_info['ndk_api']
                else:
                    dist.ndk_api = None
                    warning(
                        "Distribution {distname}: ({distdir}) has been "
                        "built with an unknown api target, ignoring it, "
                        "you might want to delete it".format(
                            distname=dist.name,
                            distdir=dist.dist_dir
                        )
                    )
                dists.append(dist)
        return dists

    def save_info(self, dirn):
        with current_directory(dirn):
            info('Saving distribution info')
            with open('dist_info.json', 'w') as fileh:
                json.dump({'dist_name': self.name,
                           'bootstrap': self.ctx.bootstrap.name,
                           'archs': [arch.arch for arch in self.ctx.archs],
                           'ndk_api': self.ctx.ndk_api,
                           'recipes': self.ctx.recipe_build_order + self.ctx.python_modules,
                           'hostpython': self.ctx.hostpython,
                           'python_version': self.ctx.python_recipe.major_minor_version_string},
                          fileh)

def _pretty_log_dists(dists, log_func=info):
    infos = []
    for dist in dists:
        ndk_api = 'unknown' if dist.ndk_api is None else dist.ndk_api
        infos.append('{Fore.GREEN}{Style.BRIGHT}{name}{Style.RESET_ALL}: min API {ndk_api}, '
                     'includes recipes ({Fore.GREEN}{recipes}'
                     '{Style.RESET_ALL}), built for archs ({Fore.BLUE}'
                     '{archs}{Style.RESET_ALL})'.format(
                         ndk_api=ndk_api,
                         name=dist.name, recipes=', '.join(dist.recipes),
                         archs=', '.join(dist.archs) if dist.archs else 'UNKNOWN',
                         Fore=Err_Fore, Style=Err_Style))
    for line in infos:
        log_func('\t' + line)

def generate_dist_folder_name(base_dist_name, arch_names = None):
    return f"{base_dist_name}__{'no_arch_specified' if arch_names is None else '_'.join(arch_names)}"
