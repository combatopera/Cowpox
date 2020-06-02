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

from .archs import ArchARM, ArchARMv7_a, ArchAarch_64, Archx86, Archx86_64
from .config import Config
from .dirs import Dirs
from .mirror import Mirror
from .recommendations import check_ndk_version, check_target_api, check_ndk_api
from diapyr import types
from importlib import import_module
from lagoon import virtualenv
from lagoon.program import Program
from os.path import join, exists, split
from p4a import CythonRecipe, Recipe
from pathlib import Path
from pkg_resources import resource_filename
from pythonforandroid.pythonpackage import get_package_name
import copy, glob, logging, os, re, subprocess

log = logging.getLogger(__name__)

def get_ndk_platform_dir(ndk_dir, ndk_api, arch):
    ndk_platform_dir_exists = True
    platform_dir = arch.platform_dir
    ndk_platform = ndk_dir / 'platforms' / f"android-{ndk_api}" / platform_dir
    if not ndk_platform.exists():
        log.warning("ndk_platform doesn't exist: %s", ndk_platform)
        ndk_platform_dir_exists = False
    return ndk_platform, ndk_platform_dir_exists

def get_toolchain_versions(ndk_dir, arch):
    toolchain_versions = []
    toolchain_path_exists = True
    toolchain_prefix = arch.toolchain_prefix
    toolchain_path = ndk_dir / 'toolchains'
    if toolchain_path.is_dir():
        toolchain_contents = glob.glob(f"{toolchain_path}/{toolchain_prefix}-*")
        toolchain_versions = [split(path)[-1][len(toolchain_prefix) + 1:] for path in toolchain_contents]
    else:
        log.warning('Could not find toolchain subdirectory!')
        toolchain_path_exists = False
    return toolchain_versions, toolchain_path_exists

def get_targets(sdk_dir):
    avdmanagerpath = sdk_dir / 'tools' / 'bin' / 'avdmanager'
    if avdmanagerpath.exists():
        return Program.text(avdmanagerpath)('list', 'target').split('\n')
    if (sdk_dir / 'tools' / 'android').exists():
        android = Program.text(sdk_dir / 'tools' / 'android')
        return android.list().split('\n')
    raise Exception('Could not find `android` or `sdkmanager` binaries in Android SDK', 'Make sure the path to the Android SDK is correct')

def _apilevels(sdk_dir):
    targets = get_targets(sdk_dir)
    apis = [s for s in targets if re.match(r'^ *API level: ', s)]
    apis = [re.findall(r'[0-9]+', s) for s in apis]
    return [int(s[0]) for s in apis if s]

class Context:

    contribroot = Path(resource_filename('pythonforandroid', '.'))
    env = os.environ.copy()
    distribution = None
    libs_dir = None
    aars_dir = None
    ndk_platform = None
    bootstrap = None
    bootstrap_build_dir = None
    recipe_build_order = None

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
    def packages_path(self):
        return self.storage_dir / 'packages'

    @property
    def libs_dir(self):
        return (self.buildsdir / 'libs_collections' / self.bootstrap.distribution.name).mkdirp()

    @property
    def javaclass_dir(self):
        return (self.buildsdir / 'javaclasses' / self.bootstrap.distribution.name).mkdirp()

    @property
    def aars_dir(self):
        return (self.buildsdir / 'aars' / self.bootstrap.distribution.name).mkdirp()

    @property
    def python_installs_dir(self):
        return (self.buildsdir / 'python-installs').mkdirp()

    def get_python_install_dir(self):
        return self.python_installs_dir / self.bootstrap.distribution.name

    def setup_dirs(self, storage_dir):
        self.buildsdir = storage_dir / 'build'
        self.distsdir = storage_dir / 'dists'
        self.storage_dir = storage_dir

    def ensure_dirs(self):
        self.storage_dir.mkdirp()
        self.buildsdir.mkdirp()
        self.distsdir.mkdirp()
        (self.buildsdir / 'bootstrap_builds').mkdirp()
        (self.buildsdir / 'other_builds').mkdirp()

    def _prepare_build_environment(self):
        self.ensure_dirs()
        log.info("Found Android API target in $ANDROIDAPI: %s", self.android_api)
        check_target_api(self.android_api, self.archs[0].arch)
        apis = _apilevels(self.sdk_dir)
        log.info("Available Android APIs are (%s)", ', '.join(map(str, apis)))
        if self.android_api not in apis:
            raise Exception("Requested API target %s is not available, install it with the SDK android tool." % self.android_api)
        log.info("Requested API target %s is available, continuing.", self.android_api)
        log.info("Found NDK dir in $ANDROIDNDK: %s", self.ndk_dir)
        check_ndk_version(self.ndk_dir)
        log.info('Getting NDK API version (i.e. minimum supported API) from user argument')
        check_ndk_api(self.ndk_api, self.android_api)
        try:
            subprocess.check_call(['python3', '-m', 'cython', '--help'])
        except subprocess.CalledProcessError:
            log.warning('Cython for python3 missing. If you are building for  a python 3 target (which is the default) then THINGS WILL BREAK.')
        arch = self.archs[0]
        toolchain_prefix = arch.toolchain_prefix
        self.ndk_platform, ndk_platform_dir_exists = get_ndk_platform_dir(self.ndk_dir, self.ndk_api, arch)
        toolchain_versions, toolchain_path_exists = get_toolchain_versions(self.ndk_dir, arch)
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

    @types(Config, Dirs, Mirror)
    def __init__(self, config, dirs, mirror):
        self.androidarch = config.android.arch
        self.ndk_api = config.android.ndk_api
        self.android_api = config.android.api
        self.sdk_dir = Path(config.android_sdk_dir)
        self.ndk_dir = Path(config.android_ndk_dir)
        self.recipes = {}
        self.include_dirs = []
        self.ndk = None
        self.toolchain_prefix = None
        self.toolchain_version = None
        self.archs = (
            ArchARM(self),
            ArchARMv7_a(self),
            Archx86(self),
            Archx86_64(self),
            ArchAarch_64(self),
        )
        self.env.pop("LDFLAGS", None)
        self.env.pop("ARCHFLAGS", None)
        self.env.pop("CFLAGS", None)
        self.dirs = dirs
        self.mirror = mirror

    def init(self):
        self.setup_dirs(self.dirs.platform_dir / f"build-{self.androidarch}")
        self.set_archs([self.androidarch])
        self._prepare_build_environment()

    def set_archs(self, arch_names):
        all_archs = self.archs
        new_archs = set()
        for name in arch_names:
            matching = [arch for arch in all_archs if arch.arch == name]
            for match in matching:
                new_archs.add(match)
        self.archs = list(new_archs)
        if not self.archs:
            raise Exception('Asked to compile for no Archs, so failing.')
        log.info("Will compile for the following archs: %s", ', '.join(arch.arch for arch in self.archs))

    def prepare_bootstrap(self, bs):
        bs.ctx = self
        self.bootstrap = bs
        self.bootstrap.prepare_build_dir()
        self.bootstrap_build_dir = self.bootstrap.build_dir

    def prepare_dist(self):
        self.bootstrap.prepare_dist_dir()

    def get_libs_dir(self, arch):
        return (self.libs_dir / arch).mkdirp()

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
        for arch in self.archs:
            log.info("Building all recipes for arch %s", arch.arch)
            log.info('Unpacking recipes')
            for recipe in recipes:
                recipe.get_build_container_dir(arch.arch).mkdirp()
                recipe.prepare_build_dir(arch.arch)
            log.info('Prebuilding recipes')
            # 2) prebuild packages
            for recipe in recipes:
                log.info("Prebuilding %s for %s", recipe.name, arch.arch)
                recipe.prebuild_arch(arch)
                recipe.apply_patches(arch)
            # 3) build packages
            log.info('Building recipes')
            for recipe in recipes:
                log.info("Building %s for %s", recipe.name, arch.arch)
                if recipe.should_build(arch):
                    recipe.build_arch(arch)
                    recipe.install_libraries(arch)
                else:
                    log.info("%s said it is already built, skipping", recipe.name)
            log.info('Postbuilding recipes')
            for recipe in recipes:
                log.info("Postbuilding %s for %s", recipe.name, arch.arch)
                recipe.postbuild_arch(arch)
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
        recipe_env = standard_recipe.get_recipe_env(self.archs[0])
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
        standard_recipe.strip_object_files(self.archs[0], env, self.buildsdir)
