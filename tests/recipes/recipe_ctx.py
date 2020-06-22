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

import os

from pythonforandroid.bootstrap import Bootstrap
from pythonforandroid.distribution import Distribution
from pythonforandroid.recipe import Recipe
from pythonforandroid.build import Context
from pythonforandroid.archs import ArchAarch_64


class RecipeCtx:
    """
    An base class for unit testing a recipe. This will create a context so we
    can test any recipe using this context. Implement `setUp` and `tearDown`
    methods used by unit testing.
    """

    ctx = None
    arch = None
    recipe = None

    recipe_name = ""
    "The name of the recipe to test."

    recipes = []
    """A List of recipes to pass to `Distribution.get_distribution`. Should
    contain the target recipe to test as well as a python recipe."""
    recipe_build_order = []
    """A recipe_build_order which should take into account the recipe we want
    to test as well as the possible dependent recipes"""

    TEST_ARCH = 'arm64-v8a'

    def setUp(self):
        self.ctx = Context()
        self.ctx.ndk_api = 21
        self.ctx.android_api = 27
        self.ctx._sdk_dir = "/opt/android/android-sdk"
        self.ctx._ndk_dir = "/opt/android/android-ndk"
        self.ctx.setup_dirs(os.getcwd())
        self.ctx.bootstrap = Bootstrap().get_bootstrap("sdl2", self.ctx)
        self.ctx.bootstrap.distribution = Distribution.get_distribution(
            self.ctx, name="sdl2", recipes=self.recipes, arch_name=self.TEST_ARCH,
        )
        self.ctx.recipe_build_order = self.recipe_build_order
        self.ctx.python_recipe = Recipe.get_recipe("python3", self.ctx)
        self.arch = ArchAarch_64(self.ctx)
        self.ctx.ndk_platform = (
            f"{self.ctx._ndk_dir}/platforms/"
            f"android-{self.ctx.ndk_api}/{self.arch.platform_dir}"
        )
        self.recipe = Recipe.get_recipe(self.recipe_name, self.ctx)

    def tearDown(self):
        self.ctx = None
