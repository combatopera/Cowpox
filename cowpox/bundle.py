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

from . import Graph, GraphInfo, PipInstallOK
from .config import Config
from .container import compileall
from .graph import GraphImpl
from .make import Make
from .pyrecipe import CythonRecipe
from .util import DIProxy
from diapyr import types
from lagoon import pip
from pathlib import Path
import logging

log = logging.getLogger(__name__)

class GraphProxy(DIProxy, Graph): targetclass = GraphImpl

class PipInstallRecipe(CythonRecipe):

    @types(Config)
    def __init(self, config):
        self.pip_install_dir = Path(config.pip.install.dir)

    @types(Make, GraphInfo, this = PipInstallOK)
    def buildsite(self, make, graphinfo):
        def target():
            yield self.pip_install_dir # FIXME: Rebuild when requirements change.
            pypinames = graphinfo.pypinames
            if pypinames:
                pip.install._v.__no_deps.print('--target', self.pip_install_dir, *pypinames, env = self.get_recipe_env())
                compileall(self.pip_install_dir)
            else:
                self.pip_install_dir.mkdirp()
        make(target)

    @property
    def bundlepackages(self):
        return self.pip_install_dir
