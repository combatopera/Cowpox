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
from .platform import Make
from .util import DIProxy
from diapyr import types
from lagoon import virtualenv
from lagoon.program import Program
from p4a import Arch, Graph
from p4a.python import GuestPythonRecipe, HostPythonRecipe
from p4a.recipe import CythonRecipe
from pathlib import Path
import logging, os

log = logging.getLogger(__name__)

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

    def get_recipe_env(self):
        env = super().get_recipe_env()
        # Make sure our build package dir is available, and the virtualenv
        # site packages come FIRST (so the proper pip version is used):
        env['PYTHONPATH'] = os.pathsep.join(map(str, [
            self.venv_path / 'lib' / f"python{self.graph.python_recipe.majminversion}" / 'site-packages',
            self.python_install_dir,
        ]))
        return env

class ContextImpl:

    @types(Config, Arch, Graph, GraphInfo, PipInstallRecipe, Make)
    def __init__(self, config, arch, graph, graphinfo, pipinstallrecipe, make):
        self.buildsdir = Path(config.buildsdir)
        self.python_install_dir = Path(config.python_install_dir)
        self.venv_path = Path(config.venv.path)
        self.arch = arch
        self.graph = graph
        self.graphinfo = graphinfo
        self.pipinstallrecipe = pipinstallrecipe
        self.make = make

    def build_recipes(self):
        for recipe in self.graph.allrecipes():
            log.info("Build recipe: %s", recipe.name)
            recipe.download_if_necessary()
            self.make(recipe.recipebuilddir, recipe.prepare_build_dir)
            self.make(recipe.recipebuilddir, recipe.mainbuild)

    def build_nonrecipes(self):
        virtualenv.print(f"--python={self.graph.python_recipe.exename}", self.venv_path)
        pip = Program.text(self.venv_path / 'bin' / 'pip')
        pip.install._U.print('pip', env = dict(PYTHONPATH = self.python_install_dir))
        pip.install.print('Cython', env = dict(PYTHONPATH = self.python_install_dir))
        pypinames = self.graphinfo.pypinames
        if pypinames:
            pip.install._v.__no_deps.print('--target', self.python_install_dir, *pypinames, env = self.pipinstallrecipe.get_recipe_env())
        self.arch.strip_object_files(self.buildsdir)
