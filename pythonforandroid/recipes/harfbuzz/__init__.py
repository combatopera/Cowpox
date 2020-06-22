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

from pythonforandroid.recipe import Recipe
from pythonforandroid.util import current_directory
from pythonforandroid.logger import shprint
from multiprocessing import cpu_count
from os.path import join
import sh


class HarfbuzzRecipe(Recipe):
    """The harfbuzz library it's special, because has cyclic dependencies with
    freetype library, so freetype can be build with harfbuzz support, and
    harfbuzz can be build with freetype support. This complicates the build of
    both recipes because in order to get the full set we need to compile those
    recipes several times:
        - build freetype without harfbuzz
        - build harfbuzz with freetype
        - build freetype with harfbuzz support

    .. seealso::
        https://sourceforge.net/projects/freetype/files/freetype2/2.5.3/
    """

    version = '0.9.40'
    url = 'http://www.freedesktop.org/software/harfbuzz/release/harfbuzz-{version}.tar.bz2'  # noqa
    opt_depends = ['freetype']
    built_libraries = {'libharfbuzz.so': 'src/.libs'}

    def get_recipe_env(self, arch=None):
        env = super(HarfbuzzRecipe, self).get_recipe_env(arch)
        if 'freetype' in self.ctx.recipe_build_order:
            freetype = self.get_recipe('freetype', self.ctx)
            freetype_install = join(
                freetype.get_build_dir(arch.arch), 'install'
            )
            # Explicitly tell harfbuzz's configure script that we want to
            # use our freetype library or it won't be correctly detected
            env['FREETYPE_CFLAGS'] = '-I{}/include/freetype2'.format(
                freetype_install
            )
            env['FREETYPE_LIBS'] = ' '.join(
                ['-L{}/lib'.format(freetype_install), '-lfreetype']
            )
        return env

    def build_arch(self, arch):

        env = self.get_recipe_env(arch)

        with current_directory(self.get_build_dir(arch.arch)):
            configure = sh.Command('./configure')
            shprint(
                configure,
                '--without-icu',
                '--host={}'.format(arch.command_prefix),
                '--prefix={}'.format(self.get_build_dir(arch.arch)),
                '--with-freetype={}'.format(
                    'yes'
                    if 'freetype' in self.ctx.recipe_build_order
                    else 'no'
                ),
                '--without-glib',
                _env=env,
            )
            shprint(sh.make, '-j', str(cpu_count()), _env=env)

        if 'freetype' in self.ctx.recipe_build_order:
            # Rebuild/install freetype with harfbuzz support
            freetype = self.get_recipe('freetype', self.ctx)
            freetype.build_arch(arch, with_harfbuzz=True)
            freetype.install_libraries(arch)


recipe = HarfbuzzRecipe()
