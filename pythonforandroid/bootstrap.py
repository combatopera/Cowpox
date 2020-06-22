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

from .util import current_directory, ensure_dir
from importlib import import_module
from lagoon import cp, find, mv, rm, unzip
from os import listdir, walk, sep
from os.path import join, isdir, normpath, splitext, basename
from p4a import Recipe
from tempfile import TemporaryDirectory
import functools, glob, logging, os, sh, shlex, shutil

log = logging.getLogger(__name__)

def _copy_files(src_root, dest_root, override):
    for root, dirnames, filenames in walk(src_root):
        for filename in filenames:
            subdir = normpath(root.replace(str(src_root), ""))
            if subdir.startswith(sep):  # ensure it is relative
                subdir = subdir[1:]
            dest_dir = join(dest_root, subdir)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
            src_file = join(root, filename)
            dest_file = join(dest_dir, filename)
            if os.path.isfile(src_file):
                if override and os.path.exists(dest_file):
                    os.unlink(dest_file)
                if not os.path.exists(dest_file):
                    shutil.copy(src_file, dest_file)
            else:
                os.makedirs(dest_file)

default_recipe_priorities = [
    "webview", "sdl2", "service_only"  # last is highest
]
# ^^ NOTE: these are just the default priorities if no special rules
# apply (which you can find in the code below), so basically if no
# known graphical lib or web lib is used - in which case service_only
# is the most reasonable guess.


def _cmp_bootstraps_by_priority(a, b):
    def rank_bootstrap(bootstrap):
        """ Returns a ranking index for each bootstrap,
            with higher priority ranked with higher number. """
        if bootstrap.name in default_recipe_priorities:
            return default_recipe_priorities.index(bootstrap.name) + 1
        return 0

    # Rank bootstraps in order:
    rank_a = rank_bootstrap(a)
    rank_b = rank_bootstrap(b)
    if rank_a != rank_b:
        return (rank_b - rank_a)
    else:
        if a.name < b.name:  # alphabetic sort for determinism
            return -1
        else:
            return 1

class Bootstrap:

    name = ''
    jni_subdir = '/jni'
    ctx = None
    build_dir = None
    distribution = None
    recipe_depends = [("python2", "python3"), 'android']
    can_be_chosen_automatically = True

    @property
    def dist_dir(self):
        return self.distribution.dist_dir

    @property
    def jni_dir(self):
        return self.name + self.jni_subdir

    def check_recipe_choices(self):
        '''Checks what recipes are being built to see which of the alternative
        and optional dependencies are being used,
        and returns a list of these.'''
        recipes = []
        built_recipes = self.ctx.recipe_build_order
        for recipe in self.recipe_depends:
            if isinstance(recipe, (tuple, list)):
                for alternative in recipe:
                    if alternative in built_recipes:
                        recipes.append(alternative)
                        break
        return sorted(recipes)

    def get_build_dir_name(self):
        choices = self.check_recipe_choices()
        dir_name = '-'.join([self.name] + choices)
        return dir_name

    def get_build_dir(self):
        return self.ctx.buildsdir / 'bootstrap_builds' / self.get_build_dir_name()

    def get_dist_dir(self, name):
        return self.ctx.distsdir / name

    @property
    def name(self):
        modname = self.__class__.__module__
        return modname.split(".", 2)[-1]

    def prepare_build_dir(self):
        '''Ensure that a build dir exists for the recipe. This same single
        dir will be used for building all different archs.'''
        self.build_dir = self.get_build_dir()
        _copy_files(self.bootstrap_dir / 'build', self.build_dir, True)
        _copy_files(join(os.path.abspath(self.bootstrap_dir / ".." / 'common'), 'build'), self.build_dir, False)
        with current_directory(self.build_dir):
            with open('project.properties', 'w') as fileh:
                fileh.write('target=android-{}'.format(self.ctx.android_api))

    def prepare_dist_dir(self):
        ensure_dir(self.dist_dir)

    def run_distribute(self):
        self.distribution.save_info(self.dist_dir)

    @classmethod
    def _all_bootstraps(cls, ctx):
        bootstraps_dir = ctx.contribroot / 'bootstraps'
        result = set()
        for name in listdir(bootstraps_dir):
            if name not in {'__pycache__', 'common'} and (bootstraps_dir / name).is_dir():
                result.add(name)
        return result

    @classmethod
    def _get_usable_bootstraps_for_recipes(cls, recipes, ctx):
        '''Returns all bootstrap whose recipe requirements do not conflict
        with the given recipes, in no particular order.'''
        log.info('Trying to find a bootstrap that matches the given recipes.')
        bootstraps = [cls.get_bootstrap(name, ctx) for name in cls._all_bootstraps(ctx)]
        acceptable_bootstraps = set()
        # Find out which bootstraps are acceptable:
        for bs in bootstraps:
            if not bs.can_be_chosen_automatically:
                continue
            possible_dependency_lists = expand_dependencies(bs.recipe_depends, ctx)
            for possible_dependencies in possible_dependency_lists:
                ok = True
                # Check if the bootstap's dependencies have an internal conflict:
                for recipe in possible_dependencies:
                    recipe = Recipe.get_recipe(recipe, ctx)
                    if any([conflict in recipes for conflict in recipe.conflicts]):
                        ok = False
                        break
                # Check if bootstrap's dependencies conflict with chosen
                # packages:
                for recipe in recipes:
                    try:
                        recipe = Recipe.get_recipe(recipe, ctx)
                    except ValueError:
                        conflicts = []
                    else:
                        conflicts = recipe.conflicts
                    if any([conflict in possible_dependencies
                            for conflict in conflicts]):
                        ok = False
                        break
                if ok and bs not in acceptable_bootstraps:
                    acceptable_bootstraps.add(bs)
        log.info("Found %s acceptable bootstraps: %s", len(acceptable_bootstraps), [bs.name for bs in acceptable_bootstraps])
        return acceptable_bootstraps

    @classmethod
    def get_bootstrap_from_recipes(cls, recipes, ctx):
        known_web_packages = {'flask'}  # to pick webview over service_only
        recipes_with_deps_lists = expand_dependencies(recipes, ctx)
        acceptable_bootstraps = cls._get_usable_bootstraps_for_recipes(recipes, ctx)
        def have_dependency_in_recipes(dep):
            for dep_list in recipes_with_deps_lists:
                if dep in dep_list:
                    return True
            return False
        # Special rule: return SDL2 bootstrap if there's an sdl2 dep:
        if (have_dependency_in_recipes("sdl2") and
                "sdl2" in [b.name for b in acceptable_bootstraps]
                ):
            log.info('Using sdl2 bootstrap since it is in dependencies')
            return cls.get_bootstrap("sdl2", ctx)
        # Special rule: return "webview" if we depend on common web recipe:
        for possible_web_dep in known_web_packages:
            if have_dependency_in_recipes(possible_web_dep):
                # We have a web package dep!
                if "webview" in [b.name for b in acceptable_bootstraps]:
                    log.info("Using webview bootstrap since common web packages were found %s", known_web_packages.intersection(recipes))
                    return cls.get_bootstrap("webview", ctx)
        prioritized_acceptable_bootstraps = sorted(
            list(acceptable_bootstraps),
            key=functools.cmp_to_key(_cmp_bootstraps_by_priority)
        )
        if prioritized_acceptable_bootstraps:
            log.info("Using the highest ranked/first of these: %s", prioritized_acceptable_bootstraps[0].name)
            return prioritized_acceptable_bootstraps[0]
        return None

    @classmethod
    def get_bootstrap(cls, name, ctx):
        bootstrap = import_module(f"pythonforandroid.bootstraps.{name}").bootstrap
        bootstrap.bootstrap_dir = ctx.contribroot / 'bootstraps' / name
        bootstrap.ctx = ctx
        return bootstrap

    def distribute_libs(self, arch, src_dirs, wildcard='*', dest_dir="libs"):
        '''Copy existing arch libs from build dirs to current dist dir.'''
        log.info('Copying libs')
        tgt_dir = join(dest_dir, arch.arch)
        ensure_dir(tgt_dir)
        for src_dir in src_dirs:
            for lib in glob.glob(join(src_dir, wildcard)):
                cp._a.print(lib, tgt_dir)

    def distribute_javaclasses(self, javaclass_dir, dest_dir="src"):
        '''Copy existing javaclasses from build dir to current dist dir.'''
        log.info('Copying java files')
        ensure_dir(dest_dir)
        for filename in glob.glob(str(javaclass_dir)):
            cp._a.print(filename, dest_dir)

    def distribute_aars(self, arch):
        '''Process existing .aar bundles and copy to current dist dir.'''
        log.info('Unpacking aars')
        for aar in glob.glob(join(self.ctx.aars_dir, '*.aar')):
            self._unpack_aar(aar, arch)

    def _unpack_aar(self, aar, arch):
        '''Unpack content of .aar bundle and copy to current dist dir.'''
        with TemporaryDirectory() as temp_dir:
            name = splitext(basename(aar))[0]
            jar_name = name + '.jar'
            log.info("unpack %s aar", name)
            log.debug("  from %s", aar)
            log.debug("  to %s", temp_dir)
            unzip._o.print(aar, '-d', temp_dir)
            jar_src = join(temp_dir, 'classes.jar')
            jar_tgt = join('libs', jar_name)
            log.debug("copy %s jar", name)
            log.debug("  from %s", jar_src)
            log.debug("  to %s", jar_tgt)
            ensure_dir('libs')
            cp._a.print(jar_src, jar_tgt)
            so_src_dir = join(temp_dir, 'jni', arch.arch)
            so_tgt_dir = join('libs', arch.arch)
            log.debug("copy %s .so", name)
            log.debug("  from %s", so_src_dir)
            log.debug("  to %s", so_tgt_dir)
            ensure_dir(so_tgt_dir)
            so_files = glob.glob(join(so_src_dir, '*.so'))
            for f in so_files:
                cp._a.print(f, so_tgt_dir)

    def strip_libraries(self, arch):
        log.info('Stripping libraries')
        env = arch.get_env()
        tokens = shlex.split(env['STRIP'])
        strip = sh.Command(str(self.ctx.ndk_dir / 'toolchains' / f"{self.ctx.toolchain_prefix}-{self.ctx.toolchain_version}" / 'prebuilt' / 'linux-x86_64' / 'bin' / tokens[0]))
        if len(tokens) > 1:
            strip = strip.bake(tokens[1:])
        libs_dir = self.dist_dir / '_python_bundle' / '_python_bundle' / 'modules'
        filens = find(libs_dir, self.dist_dir / 'libs', '-iname', '*.so').splitlines()
        log.info('Stripping libraries in private dir')
        for filen in filens:
            try:
                strip(filen, _env=env)
            except sh.ErrorReturnCode_1:
                log.debug("Failed to strip %s", filen)

    def fry_eggs(self, sitepackages):
        log.info("Frying eggs in %s", sitepackages)
        for d in listdir(sitepackages):
            rd = join(sitepackages, d)
            if isdir(rd) and d.endswith('.egg'):
                log.info("  %s", d)
                files = [join(rd, f) for f in listdir(rd) if f != 'EGG-INFO']
                if files:
                    mv._t.print(sitepackages, *files)
                rm._rf.print(d)

def expand_dependencies(recipes, ctx):
    """ This function expands to lists of all different available
        alternative recipe combinations, with the dependencies added in
        ONLY for all the not-with-alternative recipes.
        (So this is like the deps graph very simplified and incomplete, but
         hopefully good enough for most basic bootstrap compatibility checks)
    """

    # Add in all the deps of recipes where there is no alternative:
    recipes_with_deps = list(recipes)
    for entry in recipes:
        if not isinstance(entry, (tuple, list)) or len(entry) == 1:
            if isinstance(entry, (tuple, list)):
                entry = entry[0]
            try:
                recipe = Recipe.get_recipe(entry, ctx)
                recipes_with_deps += recipe.depends
            except ValueError:
                # it's a pure python package without a recipe, so we
                # don't know the dependencies...skipping for now
                pass

    # Split up lists by available alternatives:
    recipe_lists = [[]]
    for recipe in recipes_with_deps:
        if isinstance(recipe, (tuple, list)):
            new_recipe_lists = []
            for alternative in recipe:
                for old_list in recipe_lists:
                    new_list = [i for i in old_list]
                    new_list.append(alternative)
                    new_recipe_lists.append(new_list)
            recipe_lists = new_recipe_lists
        else:
            for existing_list in recipe_lists:
                existing_list.append(recipe)
    return recipe_lists
