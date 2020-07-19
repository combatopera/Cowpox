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

from . import GraphInfo, PipInstallMemo, RecipeMemo
from .config import Config
from .make import Make
from .recipe import Recipe
from .util import findimpls
from diapyr import types
from importlib import import_module
from packaging.utils import canonicalize_name
from pkgutil import iter_modules
import logging

log = logging.getLogger(__name__)

class RecipeInfo:

    def __init__(self, impl):
        self.impl = impl

class GraphInfoImpl(GraphInfo):

    @types(Config)
    def __init__(self, config):
        allimpls = {canonicalize_name(impl.name): impl
                for p in config.recipe.packages
                for m in iter_modules(import_module(p).__path__, f"{p}.")
                for impl in findimpls(import_module(m.name), Recipe)}
        memotypes = {}
        recipeinfos = {}
        pypinames = {}
        def adddepend(depend):
            if isinstance(depend, tuple):
                group = frozenset(map(canonicalize_name, depend))
                if group not in memotypes:
                    memotypes[group] = type(f"{'Or'.join(allimpls[n].__name__ for n in sorted(group))}Memo", (), {})
                return
            normdepend = canonicalize_name(depend)
            if normdepend in recipeinfos or normdepend in pypinames:
                return
            try:
                impl = allimpls[normdepend]
            except KeyError:
                pypinames[normdepend] = depend # Keep an arbitrary unnormalised name.
                return
            recipeinfos[normdepend] = RecipeInfo(impl)
            for d in impl.depends:
                adddepend(d)
        for d in ['python3', 'bdozlib', 'android', 'sdl2' if 'sdl2' == config.bootstrap.name else 'genericndkbuild', *config.requirements]:
            adddepend(d)
        for group in (k for k in memotypes if isinstance(k, frozenset)):
            intersection = sorted(recipeinfos.keys() & group)
            if not intersection:
                raise Exception("Group not satisfied: %s" % ', '.join(sorted(group)))
            log.debug("Group %s satisfied by: %s", ', '.join(sorted(group)), ', '.join(recipeinfos[normname].impl.name for normname in intersection))
        log.info("Recipes to build: %s", ', '.join(info.impl.name for info in recipeinfos.values()))
        def memotypebases():
            yield RecipeMemo
            for k, memotype in memotypes.items():
                if isinstance(k, frozenset) and normname in k:
                    yield memotype
        for normname, info in recipeinfos.items():
            memotypes[normname] = type(f"{info.impl.__name__}Memo", tuple(memotypebases()), {})
        def getdependmemotypes():
            for d in info.impl.depends:
                if isinstance(d, tuple):
                    yield memotypes[frozenset(map(canonicalize_name, d))]
                else:
                    try:
                        yield memotypes[canonicalize_name(d)]
                    except KeyError:
                        yield PipInstallMemo
        self.builders = [info.impl for info in recipeinfos.values()]
        for normname, info in recipeinfos.items():
            dependmemotypes = list(getdependmemotypes())
            @types(info.impl, Make, *dependmemotypes, this = memotypes[normname])
            def makerecipe(recipe, make, *memos):
                return make(recipe.recipebuilddir, list(memos), recipe.mainbuild)
            log.debug("%s factory depends on: %s", memotypes[normname].__name__, ', '.join(t.__name__ for t in dependmemotypes))
            self.builders.append(makerecipe)
        self.pypinames = pypinames.values()
        log.info("Requirements not found as recipes will be installed with pip: %s", ', '.join(self.pypinames))
