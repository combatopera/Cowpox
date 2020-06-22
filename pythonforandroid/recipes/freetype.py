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

from p4a import Recipe
from pythonforandroid.logger import shprint
from os.path import join, exists
from multiprocessing import cpu_count
import logging, sh

log = logging.getLogger(__name__)

class FreetypeRecipe(Recipe):
    """The freetype library it's special, because has cyclic dependencies with
    harfbuzz library, so freetype can be build with harfbuzz support, and
    harfbuzz can be build with freetype support. This complicates the build of
    both recipes because in order to get the full set we need to compile those
    recipes several times:
        - build freetype without harfbuzz
        - build harfbuzz with freetype
        - build freetype with harfbuzz support

    .. note::
        To build freetype with harfbuzz support you must add `harfbuzz` to your
        requirements, otherwise freetype will be build without harfbuzz

    .. seealso::
        https://sourceforge.net/projects/freetype/files/freetype2/2.5.3/
    """

    version = '2.5.5'
    url = 'http://download.savannah.gnu.org/releases/freetype/freetype-{version}.tar.gz'  # noqa
    built_libraries = {'libfreetype.so': 'objs/.libs'}

    def get_recipe_env(self, arch=None, with_harfbuzz=False):
        env = super(FreetypeRecipe, self).get_recipe_env(arch)
        if with_harfbuzz:
            harfbuzz_build = self.get_recipe('harfbuzz').get_build_dir(arch.arch)
            freetype_install = join(self.get_build_dir(arch.arch), 'install')
            env['CFLAGS'] = ' '.join(
                [env['CFLAGS'], '-DFT_CONFIG_OPTION_USE_HARFBUZZ']
            )

            env['HARFBUZZ_CFLAGS'] = '-I{harfbuzz} -I{harfbuzz}/src'.format(
                harfbuzz=harfbuzz_build
            )
            env['HARFBUZZ_LIBS'] = (
                '-L{freetype}/lib -lfreetype '
                '-L{harfbuzz}/src/.libs -lharfbuzz'.format(
                    freetype=freetype_install, harfbuzz=harfbuzz_build
                )
            )
        return env

    def build_arch(self, arch, with_harfbuzz=False):
        env = self.get_recipe_env(arch, with_harfbuzz=with_harfbuzz)

        harfbuzz_in_recipes = 'harfbuzz' in self.ctx.recipe_build_order
        prefix_path = self.get_build_dir(arch.arch)
        if harfbuzz_in_recipes and not with_harfbuzz:
            # This is the first time we build freetype and we modify `prefix`,
            # because we will install the compiled library so later we can
            # build harfbuzz (with freetype support) using this freetype
            # installation
            prefix_path = join(prefix_path, 'install')

        # Configure freetype library
        config_args = {
            '--host={}'.format(arch.command_prefix),
            '--prefix={}'.format(prefix_path),
            '--without-zlib',
            '--without-bzip2',
            '--with-png=no',
        }
        if not harfbuzz_in_recipes:
            log.info('Build freetype (without harfbuzz)')
            config_args = config_args.union(
                {'--disable-static', '--enable-shared', '--with-harfbuzz=no'}
            )
        elif not with_harfbuzz:
            log.info('Build freetype for First time (without harfbuzz)')
            # This time we will build our freetype library as static because we
            # want that the harfbuzz library to have the necessary freetype
            # symbols/functions, so we avoid to have two freetype shared
            # libraries which will be confusing and harder to link with them
            config_args = config_args.union(
                {'--disable-shared', '--with-harfbuzz=no'}
            )
        else:
            log.info('Build freetype for Second time (with harfbuzz)')
            config_args = config_args.union(
                {'--disable-static', '--enable-shared', '--with-harfbuzz=yes'}
            )
        log.info("Configure args are:\n\t-%s", '\n\t-'.join(config_args))
        # Build freetype library
        with self.current_directory(self.get_build_dir(arch.arch)):
            configure = sh.Command('./configure')
            shprint(configure, *config_args, _env=env)
            shprint(sh.make, '-j', str(cpu_count()), _env=env)
            if not with_harfbuzz and harfbuzz_in_recipes:
                log.info('Installing freetype (first time build without harfbuzz)')
                # First build, install the compiled lib, and clean build env
                shprint(sh.make, 'install', _env=env)
                shprint(sh.make, 'distclean', _env=env)

    def install_libraries(self, arch):
        # This library it's special because the first time we built it may not
        # generate the expected library, because it can depend on harfbuzz, so
        # we will make sure to only install it when the library exists
        if not exists(list(self.get_libraries(arch))[0]):
            return
        self.install_libs(arch, *self.get_libraries(arch))


