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

from . import GraphInfo, RecipeMemo
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
        self.groups = {}
        pypinames = {}
        g = nx.DiGraph()
        def adddepend(depend, targetname):
            if isinstance(depend, tuple):
                group = frozenset(map(canonicalize_name, depend))
                if group not in self.groups:
                    self.groups[group] = type(f"Group{chr(ord('A') + len(self.groups))}Memo", (), {})
                return
            normdepend = canonicalize_name(depend)
            try:
                impl = impls[normdepend]
            except KeyError:
                pypinames[normdepend] = depend # Keep an arbitrary unnormalised name.
                return
            g.add_node(normdepend, impl = impl)
            if targetname is not None:
                g.add_edge(normdepend, targetname)
            for d in impl.depends:
                adddepend(d, normdepend)
        for d in ['python3', 'bdozlib', 'android', 'sdl2' if 'sdl2' == config.bootstrap.name else 'genericndkbuild', *config.requirements]:
            adddepend(d, None)
        for group in self.groups:
            intersection = sorted(g.nodes & group)
            if not intersection:
                raise Exception("Group not satisfied: %s" % ', '.join(sorted(group)))
            log.debug("Group %s satisfied by: %s", ', '.join(sorted(group)), ', '.join(g.nodes[normname]['impl'].name for normname in intersection))
        self.recipeimpls = {normname: g.nodes[normname]['impl'] for normname in nx.topological_sort(g)}
        self.pypinames = [name for _, name in sorted(pypinames.items())]
        log.info("Recipe build order: %s", ', '.join(impl.name for impl in self.recipeimpls.values()))
        log.info("Requirements not found as recipes will be installed with pip: %s", ', '.join(self.pypinames))

    def builders(self):
        def memotypebases():
            yield RecipeMemo
            for group, grouptype in self.groups.items():
                if normname in group:
                    yield grouptype
        memotypes = {}
        for normname, impl in self.recipeimpls.items():
            memotypes[normname] = type(f"{impl.__name__}Memo", tuple(memotypebases()), {})
        def getdependmemotypes():
            for d in impl.depends:
                if isinstance(d, tuple):
                    yield self.groups[frozenset(map(canonicalize_name, d))]
                else:
                    try:
                        yield memotypes[canonicalize_name(d)]
                    except KeyError:
                        pass
        for normname, impl in self.recipeimpls.items():
            yield impl
            dependmemotypes = list(getdependmemotypes())
            @types(impl, Make, *dependmemotypes, this = memotypes[normname])
            def makerecipe(recipe, make, *memos):
                return make(recipe.recipebuilddir, memos, recipe.mainbuild)
            log.debug("%s factory depends on: %s", memotypes[normname].__name__, ', '.join(t.__name__ for t in dependmemotypes))
            yield makerecipe
