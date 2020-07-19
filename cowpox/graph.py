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

from . import GraphInfo, RecipeMemos
from .config import Config
from .make import Make
from .recipe import Recipe
from .util import findimpls
from diapyr import types
from importlib import import_module
from packaging.utils import canonicalize_name
from pkgutil import iter_modules
import logging, networkx as nx

log = logging.getLogger(__name__)

class GraphInfoImpl(GraphInfo):

    @types(Config)
    def __init__(self, config):
        impls = {canonicalize_name(impl.name): impl
                for p in config.recipe.packages
                for m in iter_modules(import_module(p).__path__, f"{p}.")
                for impl in findimpls(import_module(m.name), Recipe)}
        groups = set()
        pypinames = {}
        g = nx.DiGraph()
        def adddepend(depend, targetname):
            if isinstance(depend, tuple):
                groups.add(frozenset(map(canonicalize_name, depend)))
                return
            normdepend = canonicalize_name(depend)
            try:
                impl = impls[normdepend]
            except KeyError:
                pypinames[normdepend] = depend # Keep an arbitrary unnormalised name.
                return
            g.add_node(impl.name, impl = impl)
            if targetname is not None:
                g.add_edge(impl.name, targetname)
            for d in impl.depends:
                adddepend(d, impl.name)
        def checkgroups():
            names = {canonicalize_name(name): name for name in g.nodes}
            for group in sorted(groups):
                intersection = names.keys() & group
                if not intersection:
                    raise Exception("Alternatives not satisfied: %s" % ', '.join(sorted(group)))
                log.debug("Alternatives %s satisfied by: %s", ', '.join(sorted(group)), ', '.join(names[normname] for normname in sorted(intersection)))
        for d in ['python3', 'bdozlib', 'android', 'sdl2' if 'sdl2' == config.bootstrap.name else 'genericndkbuild', *config.requirements]:
            adddepend(d, None)
        checkgroups()
        self.recipes = {name: g.nodes[name]['impl'] for name in nx.topological_sort(g)}
        self.pypinames = [name for _, name in sorted(pypinames.items())]
        log.info("Recipe build order: %s", ', '.join(self.recipes.keys()))
        log.info("Requirements not found as recipes will be installed with pip: %s", ', '.join(self.pypinames))

class Graph:

    @types(GraphInfo, [Recipe])
    def __init__(self, info, recipes):
        self.recipes = {}
        for r in recipes:
            if r.name in info.recipes:
                self.recipes[r.name] = r
            else:
                log.debug("Recipe not in lookup: %s", r)

    def get_recipe(self, name):
        return self.recipes[name]

    @types(Make, this = RecipeMemos)
    def buildrecipes(self, make):
        def memos():
            for recipe in self.recipes.values():
                log.info("Build recipe: %s", recipe.name)
                yield recipe.makerecipe(make)
        return list(memos())
