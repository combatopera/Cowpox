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

from . import Graph, PipInstallMemo, RecipeMemo
from .make import Make
from .recipe import Recipe
from .util import findimpls
from aridity.config import Config
from diapyr import types
from importlib import import_module
from packaging.utils import canonicalize_name
from pkg_resources import parse_requirements
from pkgutil import iter_modules
from types import SimpleNamespace
import logging

log = logging.getLogger(__name__)

class RecipeInfo:

    def __init__(self, impl):
        self.groups = []
        self.depends = {}
        for depend in impl.depends:
            if isinstance(depend, tuple):
                self.groups.append(frozenset(map(canonicalize_name, depend)))
            else:
                self.depends[canonicalize_name(depend)] = depend
        self.impl = impl

    def dependmemotypes(self, groupmemotypes, implmemotypes):
        for group in self.groups:
            yield groupmemotypes[group]
        for normdepend in self.depends:
            yield implmemotypes.get(normdepend, PipInstallMemo)

def _namesonly(requires):
    for r in parse_requirements(requires):
        yield r.name

class GraphImpl(Graph):

    @types(Config)
    def __init__(self, config):
        allimpls = {canonicalize_name(impl.name): impl
                for p in config.recipe.packages
                for m in iter_modules(import_module(p).__path__, f"{p}.")
                for impl in findimpls(import_module(m.name), Recipe)}
        groupmemotypes = {}
        recipeinfos = {}
        pypinames = {}
        def adddepends(info):
            for group in info.groups:
                if group not in groupmemotypes:
                    groupmemotypes[group] = type(f"{'Or'.join(allimpls[normname].__name__ for normname in sorted(group))}Memo", (), {})
            for normdepend, depend in info.depends.items():
                if normdepend not in recipeinfos and normdepend not in pypinames:
                    if normdepend in allimpls:
                        recipeinfos[normdepend] = info = RecipeInfo(allimpls[normdepend])
                        adddepends(info)
                    else:
                        pypinames[normdepend] = depend # Keep an arbitrary unnormalised name.
        # TODO: Minimise depends declared here.
        adddepends(RecipeInfo(SimpleNamespace(depends = [
                'python3', 'bdozlib', 'android', 'sdl2' if 'sdl2' == config.bootstrap.name else 'genericndkbuild', *_namesonly(config.requirements)])))
        for group in groupmemotypes:
            intersection = sorted(recipeinfos.keys() & group)
            groupstr = ', '.join(sorted(group))
            if not intersection:
                raise Exception("Group not satisfied: %s" % groupstr)
            log.debug("Group %s satisfied by: %s", groupstr, ', '.join(allimpls[normname].name for normname in intersection))
        log.info("Recipes to build: %s", ', '.join(info.impl.name for info in recipeinfos.values()))
        def memotypebases():
            yield RecipeMemo
            for group, groupmemotype in groupmemotypes.items():
                if normname in group:
                    yield groupmemotype
        implmemotypes = {}
        for normname, info in recipeinfos.items():
            implmemotypes[normname] = type(f"{info.impl.__name__}Memo", tuple(memotypebases()), {})
        self.builders = [info.impl for info in recipeinfos.values()]
        for normname, info in recipeinfos.items():
            dependmemotypes = list(info.dependmemotypes(groupmemotypes, implmemotypes))
            implmemotype = implmemotypes[normname]
            @types(info.impl, Make, *dependmemotypes, this = implmemotype)
            def builder(recipe, make, *memos):
                return make(recipe.recipebuilddir, list(memos), recipe.mainbuild)
            log.debug("%s(%s) requires: %s", implmemotype.__name__, ', '.join(b.__name__ for b in implmemotype.__bases__),
                    ', '.join(t.__name__ for t in dependmemotypes) if dependmemotypes else ())
            self.builders.append(builder)
        self.pypinames = list(pypinames.values())
        log.info("Requirements not found as recipes will be installed with pip: %s", ', '.join(self.pypinames))
