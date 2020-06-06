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

from .arch import Arch
from .config import Config
from .mirror import Mirror
from .platform import Platform
from .recommendations import check_ndk_version, check_target_api, check_ndk_api
from diapyr import types
from importlib import import_module
from lagoon import virtualenv
from lagoon.program import Program
from os.path import join, exists
from p4a import CythonRecipe, Recipe
from pathlib import Path
from pkg_resources import resource_filename
from pythonforandroid.pythonpackage import get_package_name
import copy, glob, logging, os

log = logging.getLogger(__name__)

class Context:

    contribroot = Path(resource_filename('pythonforandroid', '.'))

    def all_bootstraps(self):
        return {path.name for path in (self.contribroot / 'bootstraps').iterdir() if path.name not in {'__pycache__', 'common'} and path.is_dir()}

    def get_recipe(self, name):
        try:
            return self.recipes[name]
        except KeyError:
            module = import_module(f"pythonforandroid.recipes.{name.lower()}")
            cls = Recipe
            for n in dir(module):
                obj = getattr(module, n)
                try:
                    if issubclass(obj, cls): # FIXME LATER: There could be more than one leaf.
                        cls = obj
                except TypeError:
                    pass
            self.recipes[name] = recipe = cls(self)
            return recipe

    @property
    def libs_dir(self):
        return (self.buildsdir / 'libs_collections' / self.bootstrap.distribution.name).mkdirp()

    @property
    def javaclass_dir(self):
        return (self.buildsdir / 'javaclasses' / self.bootstrap.distribution.name).mkdirp()

    @property
    def aars_dir(self):
        return (self.buildsdir / 'aars' / self.bootstrap.distribution.name).mkdirp()

    def get_python_install_dir(self):
        return (self.buildsdir / 'python-installs').mkdirp() / self.bootstrap.distribution.name

    def init(self):
        log.info("Will compile for the following arch: %s", self.arch.name)
        self.distsdir.mkdirp()
        (self.buildsdir / 'bootstrap_builds').mkdirp()
        self.other_builds.mkdirp()
        check_target_api(self.android_api, self.arch.name)
        apis = self.platform.apilevels()
        log.info("Available Android APIs are (%s)", ', '.join(map(str, apis)))
        if self.android_api not in apis:
            raise Exception("Requested API target %s is not available, install it with the SDK android tool." % self.android_api)
        log.info("Requested API target %s is available, continuing.", self.android_api)
        check_ndk_version(self.ndk_dir)
        log.info('Getting NDK API version (i.e. minimum supported API) from user argument')
        check_ndk_api(self.ndk_api, self.android_api)
        toolchain_prefix = self.arch.toolchain_prefix
        self.ndk_platform, ndk_platform_dir_exists = self.platform.get_ndk_platform_dir(self.ndk_api, self.arch)
        toolchain_versions, toolchain_path_exists = self.platform.get_toolchain_versions(self.arch)
        toolchain_versions.sort()
        toolchain_versions_gcc = [tv for tv in toolchain_versions if tv[0].isdigit()]
        if toolchain_versions:
            log.info("Found the following toolchain versions: %s", toolchain_versions)
            log.info("Picking the latest gcc toolchain, here %s", toolchain_versions_gcc[-1])
            toolchain_version = toolchain_versions_gcc[-1]
            ok = ndk_platform_dir_exists and toolchain_path_exists
        else:
            log.warning("Could not find any toolchain for %s!", toolchain_prefix)
            ok = False
        if not ok:
            raise Exception('python-for-android cannot continue due to the missing executables above')
        self.toolchain_prefix = toolchain_prefix
        self.toolchain_version = toolchain_version

    @types(Config, Mirror, Platform, Arch)
    def __init__(self, config, mirror, platform, arch):
        self.ndk_api = config.android.ndk_api
        self.android_api = config.android.api
        self.sdk_dir = Path(config.android_sdk_dir)
        self.ndk_dir = Path(config.android_ndk_dir)
        self.storage_dir = Path(config.storage_dir)
        self.distsdir = Path(config.distsdir)
        self.buildsdir = Path(config.buildsdir)
        self.packages_path = Path(config.packages_path)
        self.other_builds = Path(config.other_builds)
        self.recipes = {}
        self.env = os.environ.copy()
        self.env.pop("LDFLAGS", None)
        self.env.pop("ARCHFLAGS", None)
        self.env.pop("CFLAGS", None)
        self.mirror = mirror
        self.platform = platform
        self.arch = arch

    def prepare_bootstrap(self, bs):
        bs.ctx = self
        self.bootstrap = bs
        self.bootstrap.prepare_build_dir()

    def prepare_dist(self):
        self.bootstrap.prepare_dist_dir()

    def get_libs_dir(self, arch):
        return (self.libs_dir / arch.name).mkdirp()

    def has_lib(self, arch, lib):
        return (self.get_libs_dir(arch) / lib).exists()

    def has_package(self, name):
        # If this is a file path, it'll need special handling:
        if (name.find("/") >= 0 or name.find("\\") >= 0) and \
                name.find("://") < 0:  # (:// would indicate an url)
            if not os.path.exists(name):
                # Non-existing dir, cannot look this up.
                return False
            try:
                name = get_package_name(os.path.abspath(name))
            except ValueError:
                # Failed to look up any meaningful name.
                return False
        try:
            recipe = self.get_recipe(name)
        except ModuleNotFoundError:
            pass
        else:
            name = getattr(recipe, 'site_packages_name', None) or name
        name = name.replace('.', '/')
        site_packages_dir = self.get_python_install_dir()
        return (exists(join(site_packages_dir, name)) or
                exists(join(site_packages_dir, name + '.py')) or
                exists(join(site_packages_dir, name + '.pyc')) or
                exists(join(site_packages_dir, name + '.pyo')) or
                exists(join(site_packages_dir, name + '.so')) or
                glob.glob(f"{site_packages_dir}/{name}-*.egg"))

    def build_recipes(self, build_order, python_modules):
        # Put recipes in correct build order
        log.info("Recipe build order is %s", build_order)
        if python_modules:
            python_modules = sorted(set(python_modules))
            log.info("The requirements (%s) were not found as recipes, they will be installed with pip.", ', '.join(python_modules))
        recipes = [self.get_recipe(name) for name in build_order]
        # download is arch independent
        log.info('Downloading recipes')
        for recipe in recipes:
            recipe.download_if_necessary(self.mirror)
        log.info("Building all recipes for arch %s", self.arch.name)
        log.info('Unpacking recipes')
        for recipe in recipes:
            recipe.prepare_build_dir(self.arch)
        log.info('Prebuilding recipes')
        for recipe in recipes:
            log.info("Prebuilding %s for %s", recipe.name, self.arch.name)
            recipe.prebuild_arch(self.arch)
            recipe.apply_patches(self.arch)
        log.info('Building recipes')
        for recipe in recipes:
            log.info("Building %s for %s", recipe.name, self.arch.name)
            if recipe.should_build(self.arch):
                recipe.build_arch(self.arch)
                recipe.install_libraries(self.arch)
            else:
                log.info("%s said it is already built, skipping", recipe.name)
        log.info('Postbuilding recipes')
        for recipe in recipes:
            log.info("Postbuilding %s for %s", recipe.name, self.arch.name)
            recipe.postbuild_arch(self.arch)
        log.info('Installing pure Python modules')
        log.info('*** PYTHON PACKAGE / PROJECT INSTALL STAGE ***')
        modules = [m for m in python_modules if not self.has_package(m)]
        if not modules:
            log.info('No Python modules and no setup.py to process, skipping')
            return
        log.info("The requirements (%s) don't have recipes, attempting to install them with pip", ', '.join(modules))
        log.info('If this fails, it may mean that the module has compiled components and needs a recipe.')
        virtualenv.print(f"--python=python{self.python_recipe.major_minor_version_string.partition('.')[0]}", 'venv', cwd = self.buildsdir)
        base_env = os.environ.copy()
        base_env["PYTHONPATH"] = self.get_python_install_dir() # XXX: Really?
        log.info('Upgrade pip to latest version')
        pip = Program.text(Path('venv', 'bin', 'pip'))
        pip.install._U.print('pip', env = base_env, cwd = self.buildsdir)
        log.info('Install Cython in case one of the modules needs it to build')
        pip.install.print('Cython', env = base_env, cwd = self.buildsdir)
        # Get environment variables for build (with CC/compiler set):
        standard_recipe = CythonRecipe(self)
        # (note: following line enables explicit -lpython... linker options)
        standard_recipe.call_hostpython_via_targetpython = False
        recipe_env = standard_recipe.get_recipe_env(self.arch)
        env = copy.copy(base_env)
        env.update(recipe_env)
        # Make sure our build package dir is available, and the virtualenv
        # site packages come FIRST (so the proper pip version is used):
        env['PYTHONPATH'] = f"""{(self.buildsdir / 'venv' / 'lib' / f"python{self.python_recipe.major_minor_version_string}" / 'site-packages').resolve()}{os.pathsep}{env['PYTHONPATH']}{os.pathsep}{self.get_python_install_dir()}"""
        # Install the manually specified requirements first:
        if not modules:
            log.info('There are no Python modules to install, skipping')
        else:
            log.info('Creating a requirements.txt file for the Python modules')
            with (self.buildsdir / 'requirements.txt').open('w') as fileh:
                for module in modules:
                    key = f"VERSION_{module}" # TODO: Retire this.
                    line = f"{module}=={os.environ[key]}" if key in os.environ else module
                    print(line, file = fileh)
            log.info('Installing Python modules with pip')
            log.info('IF THIS FAILS, THE MODULES MAY NEED A RECIPE. A reason for this is often modules compiling native code that is unaware of Android cross-compilation and does not work without additional changes / workarounds.')
            pip.install._v.__no_deps.print('--target', self.get_python_install_dir(), '-r', 'requirements.txt', '-f', '/wheels', env = env, cwd = self.buildsdir)
        standard_recipe.strip_object_files(self.arch, env, self.buildsdir)
