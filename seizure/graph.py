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

def fix_deplist(deps):
    """ Turn a dependency list into lowercase, and make sure all entries
        that are just a string become a tuple of strings
    """
    deps = [
        ((dep.lower(),)
         if not isinstance(dep, (list, tuple))
         else tuple([dep_entry.lower()
                     for dep_entry in dep
                    ]))
        for dep in deps
    ]
    return deps

class RecipeOrder(dict):

    def __init__(self, ctx):
        self.ctx = ctx

    def conflicts(self):
        for name in self.keys():
            try:
                recipe = self.ctx.get_recipe(name)
                conflicts = [dep.lower() for dep in recipe.conflicts]
            except ModuleNotFoundError:
                conflicts = []
            if any([c in self for c in conflicts]):
                return True
        return False

def get_dependency_tuple_list_for_recipe(recipe, blacklist=None):
    """ Get the dependencies of a recipe with filtered out blacklist, and
        turned into tuples with fix_deplist()
    """
    if blacklist is None:
        blacklist = set()
    assert(type(blacklist) == set)
    if recipe.depends is None:
        dependencies = []
    else:
        # Turn all dependencies into tuples so that product will work
        dependencies = fix_deplist(recipe.depends)

        # Filter out blacklisted items and turn lowercase:
        dependencies = [
            tuple(set(deptuple) - blacklist)
            for deptuple in dependencies
            if tuple(set(deptuple) - blacklist)
        ]
    return dependencies


def recursively_collect_orders(
        name, ctx, all_inputs, orders=None, blacklist=None
        ):
    '''For each possible recipe ordering, try to add the new recipe name
    to that order. Recursively do the same thing with all the
    dependencies of each recipe.

    '''
    name = name.lower()
    if orders is None:
        orders = []
    if blacklist is None:
        blacklist = set()
    try:
        recipe = ctx.get_recipe(name)
        dependencies = get_dependency_tuple_list_for_recipe(recipe, blacklist = blacklist)
        # handle opt_depends: these impose requirements on the build
        # order only if already present in the list of recipes to build
        dependencies.extend(fix_deplist(
            [[d] for d in recipe.get_opt_depends_in_list(all_inputs)
             if d.lower() not in blacklist]
        ))
        if recipe.conflicts is None:
            conflicts = []
        else:
            conflicts = [dep.lower() for dep in recipe.conflicts]
    except ModuleNotFoundError:
        # The recipe does not exist, so we assume it can be installed
        # via pip with no extra dependencies
        dependencies = []
        conflicts = []
    new_orders = []
    # for each existing recipe order, see if we can add the new recipe name
    for order in orders:
        if name in order:
            new_orders.append(deepcopy(order))
            continue
        if order.conflicts():
            continue
        if any([conflict in order for conflict in conflicts]):
            continue

        for dependency_set in product(*dependencies):
            new_order = deepcopy(order)
            new_order[name] = set(dependency_set)

            dependency_new_orders = [new_order]
            for dependency in dependency_set:
                dependency_new_orders = recursively_collect_orders(
                    dependency, ctx, all_inputs, dependency_new_orders,
                    blacklist=blacklist
                )

            new_orders.extend(dependency_new_orders)

    return new_orders


def find_order(graph):
    '''
    Do a topological sort on the dependency graph dict.
    '''
    while graph:
        # Find all items without a parent
        leftmost = [l for l, s in graph.items() if not s]
        if not leftmost:
            raise ValueError('Dependency cycle detected! %s' % graph)
        # If there is more than one, sort them for predictable order
        leftmost.sort()
        for result in leftmost:
            # Yield and remove them from the graph
            yield result
            graph.pop(result)
            for bset in graph.values():
                bset.discard(result)


def obvious_conflict_checker(ctx, name_tuples, blacklist=None):
    """ This is a pre-flight check function that will completely ignore
        recipe order or choosing an actual value in any of the multiple
        choice tuples/dependencies, and just do a very basic obvious
        conflict check.
    """
    deps_were_added_by = dict()
    deps = set()
    if blacklist is None:
        blacklist = set()

    # Add dependencies for all recipes:
    to_be_added = [(name_tuple, None) for name_tuple in name_tuples]
    while len(to_be_added) > 0:
        current_to_be_added = list(to_be_added)
        to_be_added = []
        for (added_tuple, adding_recipe) in current_to_be_added:
            assert(type(added_tuple) == tuple)
            if len(added_tuple) > 1:
                # No obvious commitment in what to add, don't check it itself
                # but throw it into deps for later comparing against
                # (Remember this function only catches obvious issues)
                deps.add(added_tuple)
                continue

            name = added_tuple[0]
            recipe_conflicts = set()
            recipe_dependencies = []
            try:
                # Get recipe to add and who's ultimately adding it:
                recipe = ctx.get_recipe(name)
                recipe_conflicts = {c.lower() for c in recipe.conflicts}
                recipe_dependencies = get_dependency_tuple_list_for_recipe(
                    recipe, blacklist=blacklist
                )
            except ModuleNotFoundError:
                pass
            adder_first_recipe_name = adding_recipe or name

            # Collect the conflicts:
            triggered_conflicts = []
            for dep_tuple_list in deps:
                # See if the new deps conflict with things added before:
                if set(dep_tuple_list).intersection(
                       recipe_conflicts) == set(dep_tuple_list):
                    triggered_conflicts.append(dep_tuple_list)
                    continue

                # See if what was added before conflicts with the new deps:
                if len(dep_tuple_list) > 1:
                    # Not an obvious commitment to a specific recipe/dep
                    # to be added, so we won't check.
                    # (remember this function only catches obvious issues)
                    continue
                try:
                    dep_recipe = ctx.get_recipe(dep_tuple_list[0])
                except ModuleNotFoundError:
                    continue
                conflicts = [c.lower() for c in dep_recipe.conflicts]
                if name in conflicts:
                    triggered_conflicts.append(dep_tuple_list)

            # Throw error on conflict:
            if triggered_conflicts:
                # Get first conflict and see who added that one:
                adder_second_recipe_name = "'||'".join(triggered_conflicts[0])
                second_recipe_original_adder = deps_were_added_by.get(
                    (adder_second_recipe_name,), None
                )
                if second_recipe_original_adder:
                    adder_second_recipe_name = second_recipe_original_adder

                # Prompt error:
                raise Exception(
                    "Conflict detected: '{}'"
                    " inducing dependencies {}, and '{}'"
                    " inducing conflicting dependencies {}".format(
                        adder_first_recipe_name,
                        (recipe.name,),
                        adder_second_recipe_name,
                        triggered_conflicts[0]
                    ))

            # Actually add it to our list:
            deps.add(added_tuple)
            deps_were_added_by[added_tuple] = adding_recipe

            # Schedule dependencies to be added
            to_be_added += [
                (dep, adder_first_recipe_name or name)
                for dep in recipe_dependencies
                if dep not in deps
            ]
    # If we came here, then there were no obvious conflicts.
    return None

def get_recipe_order(ctx, names, bs_recipe_depends, blacklist):
    # Get set of recipe/dependency names, clean up and add bootstrap deps:
    names = set(names) | set(bs_recipe_depends)
    names = fix_deplist([
        ([name] if not isinstance(name, (list, tuple)) else name)
        for name in names
    ])
    blacklist = set() if blacklist is None else {bitem.lower() for bitem in blacklist}
    # Remove all values that are in the blacklist:
    names_before_blacklist = list(names)
    names = []
    for name in names_before_blacklist:
        cleaned_up_tuple = tuple([
            item for item in name if item not in blacklist
        ])
        if cleaned_up_tuple:
            names.append(cleaned_up_tuple)

    # Do check for obvious conflicts (that would trigger in any order, and
    # without comitting to any specific choice in a multi-choice tuple of
    # dependencies):
    obvious_conflict_checker(ctx, names, blacklist=blacklist)
    # If we get here, no obvious conflicts!

    # get all possible order graphs, as names may include tuples/lists
    # of alternative dependencies
    possible_orders = []
    for name_set in product(*names):
        new_possible_orders = [RecipeOrder(ctx)]
        for name in name_set:
            new_possible_orders = recursively_collect_orders(
                name, ctx, name_set, orders=new_possible_orders,
                blacklist=blacklist
            )
        possible_orders.extend(new_possible_orders)

    # turn each order graph into a linear list if possible
    orders = []
    for possible_order in possible_orders:
        try:
            order = find_order(possible_order)
        except ValueError:  # a circular dependency was found
            log.info("Circular dependency found in graph %s, skipping it.", possible_order)
            continue
        orders.append(list(order))

    # prefer python3 and SDL2 if available
    orders = sorted(orders,
                    key=lambda order: -('python3' in order) - ('sdl2' in order))

    if not orders:
        raise Exception(
            'Didn\'t find any valid dependency graphs. '
            'This means that some of your '
            'requirements pull in conflicting dependencies.')

    # It would be better to check against possible orders other
    # than the first one, but in practice clashes will be rare,
    # and can be resolved by specifying more parameters
    chosen_order = orders[0]
    if len(orders) > 1:
        log.info('Found multiple valid dependency orders:')
        for order in orders:
            log.info("    %s", order)
        log.info("Using the first of these: %s", chosen_order)
    else:
        log.info("Found a single valid recipe set: %s", chosen_order)
    raise Exception('boom')
    recipes = []
    python_modules = []
    for name in chosen_order:
        try:
            recipe = ctx.get_recipe(name)
            python_modules += recipe.python_depends
        except ModuleNotFoundError:
            python_modules.append(name)
        else:
            recipes.append(name)
    return recipes, list(set(python_modules))
