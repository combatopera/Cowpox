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

from .config import Config
from .graph import GraphImpl, GraphInfo
from .platform import Platform
from .recommendations import check_ndk_version, check_target_api, check_ndk_api
from .util import DIProxy
from diapyr import types
from lagoon import virtualenv
from lagoon.program import Program
from p4a import Arch, Context, Graph
from p4a.python import GuestPythonRecipe, HostPythonRecipe
from p4a.recipe import CythonRecipe
from pathlib import Path
import logging, os

log = logging.getLogger(__name__)

class Checks:

    @types(Config, Platform, Arch)
    def __init__(self, config, platform, arch):
        self.ndk_api = config.android.ndk_api
        self.android_api = config.android.api
        self.ndk_dir = Path(config.android_ndk_dir)
        self.platform = platform
        self.arch = arch

    def check(self):
        check_target_api(self.android_api, self.arch.name)
        apis = self.platform.apilevels()
        log.info("Available Android APIs are (%s)", ', '.join(map(str, apis)))
        if self.android_api not in apis:
            raise Exception("Requested API target %s is not available, install it with the SDK android tool." % self.android_api)
        log.info("Requested API target %s is available, continuing.", self.android_api)
        check_ndk_version(self.ndk_dir)
        check_ndk_api(self.ndk_api, self.android_api)

class GraphProxy(DIProxy, Graph):

    targetclass = GraphImpl

    @property
    def python_recipe(self):
        return self.di(GuestPythonRecipe)

    @property
    def host_recipe(self):
        return self.di(HostPythonRecipe)

class PipInstallRecipe(CythonRecipe):

    @types(Config)
    def __init(self, config):
        self.venv_path = Path(config.venv.path)
        self.python_install_dir = config.python_install_dir

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        # Make sure our build package dir is available, and the virtualenv
        # site packages come FIRST (so the proper pip version is used):
        env['PYTHONPATH'] = os.pathsep.join(map(str, [
            self.venv_path / 'lib' / f"python{self.graph.python_recipe.major_minor_version_string}" / 'site-packages',
            self.python_install_dir,
        ]))
        return env

class ContextImpl:

    @types(Config, Arch, Graph, GraphInfo, PipInstallRecipe, Context)
    def __init__(self, config, arch, graph, graphinfo, pipinstallrecipe, context):
        self.buildsdir = Path(config.buildsdir)
        self.python_install_dir = Path(config.python_install_dir)
        self.venv_path = Path(config.venv.path)
        self.arch = arch
        self.graph = graph
        self.graphinfo = graphinfo
        self.pipinstallrecipe = pipinstallrecipe
        self.context = context

    def build_recipes(self):
        log.info("Will compile for the following arch: %s", self.arch.name)
        recipes = self.graph.allrecipes()
        log.info('Downloading recipes')
        for recipe in recipes:
            recipe.download_if_necessary()
        log.info("Building all recipes for arch %s", self.arch.name)
        log.info('Unpacking recipes')
        for recipe in recipes:
            recipe.prepare_build_dir()
        log.info('Prebuilding recipes')
        for recipe in recipes:
            log.info("Prebuilding %s for %s", recipe.name, self.arch.name)
            recipe.prebuild_arch()
            recipe.apply_patches()
        log.info('Building recipes')
        for recipe in recipes:
            log.info("Building %s for %s", recipe.name, self.arch.name)
            if recipe.should_build():
                recipe.build_arch()
                recipe.install_libraries()
            else:
                log.info("%s said it is already built, skipping", recipe.name)
        log.info('Postbuilding recipes')
        for recipe in recipes:
            log.info("Postbuilding %s for %s", recipe.name, self.arch.name)
            recipe.postbuild_arch()
        log.info('Installing pure Python modules')
        log.info('*** PYTHON PACKAGE / PROJECT INSTALL STAGE ***')
        pypinames = [m for m in self.graphinfo.pypinames if not self.context.insitepackages(m)]
        if not pypinames:
            log.info('No Python modules and no setup.py to process, skipping')
            return
        log.info("The requirements (%s) don't have recipes, attempting to install them with pip", ', '.join(pypinames))
        log.info('If this fails, it may mean that the module has compiled components and needs a recipe.')
        virtualenv.print(f"--python=python{self.graph.python_recipe.major_minor_version_string.partition('.')[0]}", self.venv_path)
        log.info('Upgrade pip to latest version')
        pip = Program.text(self.venv_path / 'bin' / 'pip')
        pip.install._U.print('pip', env = dict(PYTHONPATH = self.python_install_dir))
        log.info('Install Cython in case one of the modules needs it to build')
        pip.install.print('Cython', env = dict(PYTHONPATH = self.python_install_dir))
        if pypinames:
            log.info('Installing Python modules with pip')
            log.info('IF THIS FAILS, THE MODULES MAY NEED A RECIPE. A reason for this is often modules compiling native code that is unaware of Android cross-compilation and does not work without additional changes / workarounds.')
            # Get environment variables for build (with CC/compiler set):
            pip.install._v.__no_deps.print('--target', self.python_install_dir.pmkdirp(), *pypinames, env = self.pipinstallrecipe.get_recipe_env(self.arch))
        else:
            log.info('There are no Python modules to install, skipping')
        self.arch.strip_object_files(self.buildsdir)
