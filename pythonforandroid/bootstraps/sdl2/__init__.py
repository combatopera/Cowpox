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

from lagoon import cp, rm
from p4a.boot import Bootstrap
from pathlib import Path
import logging

log = logging.getLogger(__name__)

class SDL2GradleBootstrap(Bootstrap):

    name = 'sdl2'
    recipe_depends = list(set(Bootstrap.recipe_depends) | {'sdl2'})

    def run_distribute(self):
        log.info("Creating Android project (%s)", self.name)
        log.info("Copying SDL2/gradle build for %s", self.arch.name)
        rm._rf.print(self.dist_dir)
        cp._r.print(self.build_dir, self.dist_dir)
        self.writelocalproperties()
        log.info('Copying Python distribution')
        self.distribute_libs(self.arch, self.arch.libs_dir)
        self.distribute_javaclasses(dest_dir = Path('src', 'main', 'java'))
        site_packages_dir = self.graph.python_recipe.create_python_bundle()
        if 'sqlite3' not in self.graphinfo.recipenames:
            with (self.dist_dir / 'blacklist.txt').open('a') as fileh:
                fileh.write('\nsqlite3/*\nlib-dynload/_sqlite3.so\n')
        self.strip_libraries()
        self.fry_eggs(site_packages_dir)
        super().run_distribute()
