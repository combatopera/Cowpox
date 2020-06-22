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

from os.path import exists, join
from pythonforandroid.logger import shprint
from p4a import Recipe
from pythonforandroid.util import current_directory
import logging, sh

log = logging.getLogger(__name__)

class LibGlobRecipe(Recipe):
    """Make a glob.h and glob.so for the python_install_dir()"""
    version = '0.0.1'
    url = None
    #
    # glob.h and glob.c extracted from
    # https://github.com/white-gecko/TokyoCabinet, e.g.:
    #   https://raw.githubusercontent.com/white-gecko/TokyoCabinet/master/glob.h
    #   https://raw.githubusercontent.com/white-gecko/TokyoCabinet/master/glob.c
    # and pushed in via patch
    name = 'libglob'
    built_libraries = {'libglob.so': '.'}

    depends = [('hostpython2', 'hostpython3')]
    patches = ['glob.patch']

    def should_build(self, arch):
        """It's faster to build than check"""
        return True

    def prebuild_arch(self, arch):
        """Make the build and target directories"""
        path = self.get_build_dir(arch.arch)
        if not exists(path):
            log.info("creating %s", path)
            shprint(sh.mkdir, '-p', path)

    def build_arch(self, arch):
        """simple shared compile"""
        env = self.get_recipe_env(arch, with_flags_in_cc=False)
        for path in (
                self.get_build_dir(arch.arch),
                join(self.ctx.python_recipe.get_build_dir(arch.arch), 'Lib'),
                join(self.ctx.python_recipe.get_build_dir(arch.arch), 'Include')):
            if not exists(path):
                log.info("creating %s", path)
                shprint(sh.mkdir, '-p', path)
        cli = env['CC'].split()[0]
        # makes sure first CC command is the compiler rather than ccache, refs:
        # https://github.com/kivy/python-for-android/issues/1399
        if 'ccache' in cli:
            cli = env['CC'].split()[1]
        cc = sh.Command(cli)

        with current_directory(self.get_build_dir(arch.arch)):
            cflags = env['CFLAGS'].split()
            cflags.extend(['-I.', '-c', '-l.', 'glob.c', '-I.'])
            shprint(cc, *cflags, _env=env)
            cflags = env['CFLAGS'].split()
            cflags.extend(['-shared', '-I.', 'glob.o', '-o', 'libglob.so'])
            cflags.extend(env['LDFLAGS'].split())
            shprint(cc, *cflags, _env=env)

