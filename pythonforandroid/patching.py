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

from os import uname
from distutils.version import LooseVersion


def check_all(*callables):
    def check(**kwargs):
        return all(c(**kwargs) for c in callables)
    return check


def check_any(*callables):
    def check(**kwargs):
        return any(c(**kwargs) for c in callables)
    return check


def is_platform(platform):
    def is_x(**kwargs):
        return uname()[0] == platform
    return is_x


is_linux = is_platform('Linux')
is_darwin = is_platform('Darwin')


def is_arch(xarch):
    def is_x(arch, **kwargs):
        return arch.arch == xarch
    return is_x


def is_api_gt(apiver):
    def is_x(recipe, **kwargs):
        return recipe.ctx.android_api > apiver
    return is_x


def is_api_gte(apiver):
    def is_x(recipe, **kwargs):
        return recipe.ctx.android_api >= apiver
    return is_x


def is_api_lt(apiver):
    def is_x(recipe, **kwargs):
        return recipe.ctx.android_api < apiver
    return is_x


def is_api_lte(apiver):
    def is_x(recipe, **kwargs):
        return recipe.ctx.android_api <= apiver
    return is_x


def is_api(apiver):
    def is_x(recipe, **kwargs):
        return recipe.ctx.android_api == apiver
    return is_x


def will_build(recipe_name):
    def will(recipe, **kwargs):
        return recipe_name in recipe.ctx.recipe_build_order
    return will


def is_ndk(ndk):
    def is_x(recipe, **kwargs):
        return recipe.ctx.ndk == ndk
    return is_x


def is_version_gt(version):
    def is_x(recipe, **kwargs):
        return LooseVersion(recipe.version) > version


def is_version_lt(version):
    def is_x(recipe, **kwargs):
        return LooseVersion(recipe.version) < version
    return is_x


def version_starts_with(version):
    def is_x(recipe, **kwargs):
        return recipe.version.startswith(version)
    return is_x
