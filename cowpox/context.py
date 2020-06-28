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

from .boot import SkeletonOK
from .config import Config
from .graph import GraphImpl
from .platform import Make
from .util import DIProxy
from diapyr import types
from lagoon import virtualenv
from lagoon.program import Program
from p4a import Graph
from p4a.python import GuestPythonRecipe, HostPythonRecipe
from p4a.recipe import CythonRecipe
from pathlib import Path
from pkg_resources import get_distribution
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

class RecipesOK: pass

class SiteOK: pass

class PipInstallRecipe(CythonRecipe):

    @types(Config)
    def __init(self, config):
        self.venv_path = Path(config.venv.path)
        self.python_install_dir = config.python_install_dir
        self.buildsdir = Path(config.buildsdir)

    @types(RecipesOK, this = SiteOK)
    def buildsite(self, _):
        pythonrecipe = self.graph.python_recipe
        virtualenv.print('--python', pythonrecipe.exename, self.venv_path)
        pip = Program.text(self.venv_path / 'bin' / 'pip')
        pip.install.print(get_distribution('Cython').as_requirement(), env = dict(PYTHONPATH = self.python_install_dir))
        installenv = self.get_recipe_env()
        installenv['PYTHONPATH'] = os.pathsep.join(map(str, [
            self.venv_path / 'lib' / f"python{pythonrecipe.majminversion}" / 'site-packages',
            self.python_install_dir,
        ]))
        pypinames = self.graphinfo.pypinames
        if pypinames:
            pip.install._v.__no_deps.print('--target', self.python_install_dir, *pypinames, env = installenv)
        self.arch.strip_object_files(self.buildsdir) # XXX: What's this for?

@types(Graph, Make, SkeletonOK, this = RecipesOK)
def buildrecipes(self, graph, make, _):
    for recipe in graph.allrecipes():
        log.info("Build recipe: %s", recipe.name)
        recipe.download_if_necessary()
        make(recipe.recipebuilddir, recipe.prepare_build_dir)
        make(recipe.recipebuilddir, recipe.mainbuild)
