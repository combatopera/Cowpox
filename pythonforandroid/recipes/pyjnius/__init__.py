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

from cowpox.config import Config
from cowpox.pyrecipe import CythonRecipe
from diapyr import types
from lagoon import cp
from pathlib import Path
import logging

log = logging.getLogger(__name__)

class PyjniusRecipe(CythonRecipe):

    version = '1.2.1'
    url = f"https://github.com/kivy/pyjnius/archive/{version}.zip"
    depends = [('genericndkbuild', 'sdl2'), 'six']

    @types(Config)
    def __init(self, config):
        self.javaclass_dir = Path(config.javaclass_dir)

    def mainbuild(self):
        if 'sdl2' in self.graphinfo.recipenames:
            self.apply_patch('sdl2_jnienv_getter.patch')
        if 'genericndkbuild' in self.graphinfo.recipenames:
            self.apply_patch('genericndkbuild_jnienv_getter.patch')
        self.install_python_package()
        log.info('Copying pyjnius java class to classes build dir')
        cp._a.print(self.recipebuilddir / 'jnius' / 'src' / 'org', self.javaclass_dir.mkdirp())
