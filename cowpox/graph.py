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
from .util import findimpls, NoSuchPluginException
from copy import deepcopy
from diapyr import types
from importlib import import_module
from itertools import product
from packaging.utils import canonicalize_name
from pkgutil import iter_modules
import logging

log = logging.getLogger(__name__)

def _fix_deplist(deps):
    return [((dep.lower(),) if not isinstance(dep, (list, tuple)) else tuple(x.lower() for x in dep)) for dep in deps]

def _get_dependency_tuple_list_for_recipe(recipe, blacklist):
    if blacklist is None:
        blacklist = set()
    return [t for t in (tuple(set(deptuple) - blacklist) for deptuple in _fix_deplist(recipe.depends)) if t]

def _recursively_collect_orders(name, all_inputs, orders, blacklist, recipeimpl):
    name = name.lower()
    if orders is None:
        orders = []
    if blacklist is None:
        blacklist = set()
    try:
        recipe = recipeimpl(name)
        dependencies = _get_dependency_tuple_list_for_recipe(recipe, blacklist)
        dependencies.extend(_fix_deplist([[d] for d in all_inputs if d in recipe.opt_depends and d.lower() not in blacklist]))
    except NoSuchPluginException:
        dependencies = []
    new_orders = []
    for order in orders:
        if name in order:
            new_orders.append(deepcopy(order))
            continue
        for dependency_set in product(*dependencies):
            new_order = deepcopy(order)
            new_order[name] = set(dependency_set)
            dependency_new_orders = [new_order]
            for dependency in dependency_set:
                dependency_new_orders = _recursively_collect_orders(dependency, all_inputs, dependency_new_orders, blacklist, recipeimpl)
            new_orders.extend(dependency_new_orders)
    return new_orders

def _find_order(graph):
    while graph:
        leftmost = [l for l, s in graph.items() if not s]
        if not leftmost:
            raise ValueError('Dependency cycle detected! %s' % graph)
        leftmost.sort()
        for result in leftmost:
            yield result
            graph.pop(result)
            for bset in graph.values():
                bset.discard(result)

class GraphInfoImpl(GraphInfo):

    @types(Config)
    def __init__(self, config):
        self.nametoimpl = {canonicalize_name(impl.name): impl
                for p in config.recipe.packages
                for m in iter_modules(import_module(p).__path__, f"{p}.")
                for impl in findimpls(import_module(m.name), Recipe)}
        # FIXME LATER: Overhaul logic so we don't have to exclude genericndkbuild every time.
        self.recipenames, self.pypinames = _get_recipe_order({'python3', 'bdozlib', 'android', *config.requirements, 'sdl2' if 'sdl2' == config.bootstrap.name else 'genericndkbuild'}, ['genericndkbuild'], self._recipeimpl)
        log.info("Recipe build order is %s", self.recipenames)
        log.info("The requirements (%s) were not found as recipes, they will be installed with pip.", ', '.join(self.pypinames))

    def _recipeimpl(self, name):
        try:
            return self.nametoimpl[canonicalize_name(name)]
        except KeyError:
            raise NoSuchPluginException(name)

    def recipeimpls(self):
        for name in self.recipenames:
            yield self._recipeimpl(name)

class GraphImpl:

    @types(GraphInfo, [Recipe])
    def __init__(self, info, recipes):
        self.recipes = {}
        names = set(info.recipenames)
        for r in recipes:
            if r.name in names:
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

def _get_recipe_order(names, blacklist, recipeimpl):
    names = _fix_deplist([([name] if not isinstance(name, (list, tuple)) else name) for name in names])
    blacklist = set() if blacklist is None else {bitem.lower() for bitem in blacklist}
    names_before_blacklist = list(names)
    names = []
    for name in names_before_blacklist:
        cleaned_up_tuple = tuple(item for item in name if item not in blacklist)
        if cleaned_up_tuple:
            names.append(cleaned_up_tuple)
    possible_orders = []
    for name_set in product(*names):
        new_possible_orders = [{}]
        for name in name_set:
            new_possible_orders = _recursively_collect_orders(name, name_set, new_possible_orders, blacklist, recipeimpl)
        possible_orders.extend(new_possible_orders)
    orders = []
    for possible_order in possible_orders:
        try:
            order = _find_order(possible_order)
        except ValueError:
            log.info("Circular dependency found in graph %s, skipping it.", possible_order)
            continue
        orders.append(list(order))
    orders = sorted(orders, key = lambda order: -('python3' in order) - ('sdl2' in order))
    if not orders:
        raise Exception('''Didn't find any valid dependency graphs. This means that some of your requirements pull in conflicting dependencies.''')
    chosen_order = orders[0]
    if len(orders) > 1:
        log.info('Found multiple valid dependency orders:')
        for order in orders:
            log.info("    %s", order)
        log.info("Using the first of these: %s", chosen_order)
        raise Exception('Investigate.')
    else:
        log.info("Found a single valid recipe set: %s", chosen_order)
    recipenames = []
    pypinames = []
    for name in chosen_order:
        try:
            recipeimpl(name)
        except NoSuchPluginException:
            pypinames.append(name)
        else:
            recipenames.append(name)
    pypinames = set(pypinames)
    assert not set(recipenames) & pypinames
    return recipenames, sorted(pypinames)
