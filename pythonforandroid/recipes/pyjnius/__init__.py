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

from pythonforandroid.recipe import CythonRecipe
from pythonforandroid.toolchain import shprint, current_directory, info
from pythonforandroid.patching import will_build
import sh
from os.path import join


class PyjniusRecipe(CythonRecipe):
    # "6553ad4" is one commit after last release (1.2.0)
    # it fixes method resolution, required for resolving requestPermissions()
    version = '1.2.1'
    url = 'https://github.com/kivy/pyjnius/archive/{version}.zip'
    name = 'pyjnius'
    depends = [('genericndkbuild', 'sdl2'), 'six']
    site_packages_name = 'jnius'

    patches = [('sdl2_jnienv_getter.patch', will_build('sdl2')),
               ('genericndkbuild_jnienv_getter.patch', will_build('genericndkbuild'))]

    def postbuild_arch(self, arch):
        super(PyjniusRecipe, self).postbuild_arch(arch)
        info('Copying pyjnius java class to classes build dir')
        with current_directory(self.get_build_dir(arch.arch)):
            shprint(sh.cp, '-a', join('jnius', 'src', 'org'), self.ctx.javaclass_dir)


recipe = PyjniusRecipe()
