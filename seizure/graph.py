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

from copy import deepcopy
from itertools import product
import logging

log = logging.getLogger(__name__)

def _fix_deplist(deps):
    return [((dep.lower(),) if not isinstance(dep, (list, tuple)) else tuple(x.lower() for x in dep)) for dep in deps]

class RecipeOrder(dict):

    def __init__(self, ctx):
        self.ctx = ctx

    def conflicts(self):
        for name in self:
            try:
                conflicts = [dep.lower() for dep in self.ctx.get_recipe(name).conflicts]
            except ModuleNotFoundError:
                conflicts = []
            if any(c in self for c in conflicts):
                return True

def _get_dependency_tuple_list_for_recipe(recipe, blacklist):
    if blacklist is None:
        blacklist = set()
    if recipe.depends is None:
        return []
    return [t for t in (tuple(set(deptuple) - blacklist) for deptuple in _fix_deplist(recipe.depends)) if t]

def _recursively_collect_orders(name, ctx, all_inputs, orders, blacklist):
    name = name.lower()
    if orders is None:
        orders = []
    if blacklist is None:
        blacklist = set()
    try:
        recipe = ctx.get_recipe(name)
        dependencies = _get_dependency_tuple_list_for_recipe(recipe, blacklist)
        dependencies.extend(_fix_deplist([[d] for d in recipe.get_opt_depends_in_list(all_inputs) if d.lower() not in blacklist]))
        conflicts = [] if recipe.conflicts is None else [dep.lower() for dep in recipe.conflicts]
    except ModuleNotFoundError:
        dependencies = []
        conflicts = []
    new_orders = []
    for order in orders:
        if name in order:
            new_orders.append(deepcopy(order))
            continue
        if order.conflicts():
            continue
        if any(conflict in order for conflict in conflicts):
            continue
        for dependency_set in product(*dependencies):
            new_order = deepcopy(order)
            new_order[name] = set(dependency_set)
            dependency_new_orders = [new_order]
            for dependency in dependency_set:
                dependency_new_orders = _recursively_collect_orders(dependency, ctx, all_inputs, dependency_new_orders, blacklist)
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

def _obvious_conflict_checker(ctx, name_tuples, blacklist):
    deps_were_added_by = {}
    deps = set()
    if blacklist is None:
        blacklist = set()
    to_be_added = [(name_tuple, None) for name_tuple in name_tuples]
    while to_be_added:
        current_to_be_added = list(to_be_added)
        to_be_added = []
        for added_tuple, adding_recipe in current_to_be_added:
            if len(added_tuple) > 1:
                deps.add(added_tuple)
                continue
            name = added_tuple[0]
            recipe_conflicts = set()
            recipe_dependencies = []
            try:
                recipe = ctx.get_recipe(name)
                recipe_conflicts = {c.lower() for c in recipe.conflicts}
                recipe_dependencies = _get_dependency_tuple_list_for_recipe(recipe, blacklist)
            except ModuleNotFoundError:
                pass
            adder_first_recipe_name = adding_recipe or name
            triggered_conflicts = []
            for dep_tuple_list in deps:
                if set(dep_tuple_list).intersection(recipe_conflicts) == set(dep_tuple_list):
                    triggered_conflicts.append(dep_tuple_list)
                    continue
                if len(dep_tuple_list) > 1:
                    continue
                try:
                    dep_recipe = ctx.get_recipe(dep_tuple_list[0])
                except ModuleNotFoundError:
                    continue
                conflicts = [c.lower() for c in dep_recipe.conflicts]
                if name in conflicts:
                    triggered_conflicts.append(dep_tuple_list)
            if triggered_conflicts:
                adder_second_recipe_name = "'||'".join(triggered_conflicts[0])
                second_recipe_original_adder = deps_were_added_by.get((adder_second_recipe_name,), None)
                if second_recipe_original_adder:
                    adder_second_recipe_name = second_recipe_original_adder
                raise Exception(f"Conflict detected: '{adder_first_recipe_name}' inducing dependencies {(recipe.name,)}, and '{adder_second_recipe_name}' inducing conflicting dependencies {triggered_conflicts[0]}")
            deps.add(added_tuple)
            deps_were_added_by[added_tuple] = adding_recipe
            to_be_added += [(dep, adder_first_recipe_name or name) for dep in recipe_dependencies if dep not in deps]

def get_recipe_order(ctx, names, bs_recipe_depends, blacklist):
    names = set(names) | set(bs_recipe_depends)
    names = _fix_deplist([([name] if not isinstance(name, (list, tuple)) else name) for name in names])
    blacklist = set() if blacklist is None else {bitem.lower() for bitem in blacklist}
    names_before_blacklist = list(names)
    names = []
    for name in names_before_blacklist:
        cleaned_up_tuple = tuple(item for item in name if item not in blacklist)
        if cleaned_up_tuple:
            names.append(cleaned_up_tuple)
    _obvious_conflict_checker(ctx, names, blacklist)
    possible_orders = []
    for name_set in product(*names):
        new_possible_orders = [RecipeOrder(ctx)]
        for name in name_set:
            new_possible_orders = _recursively_collect_orders(name, ctx, name_set, new_possible_orders, blacklist)
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
    recipes = []
    python_modules = []
    for name in chosen_order:
        try:
            python_modules += ctx.get_recipe(name).python_depends
        except ModuleNotFoundError:
            python_modules.append(name)
        else:
            recipes.append(name)
    return recipes, list(set(python_modules))
