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

from lagoon import mkdir
from p4a.recipe import NDKRecipe
import shutil

class Sqlite3Recipe(NDKRecipe):

    version = '3.15.1'
    url = 'https://www.sqlite.org/2016/sqlite-amalgamation-3150100.zip'
    generated_libraries = ['sqlite3']

    def should_build(self):
        return not self.has_libs('libsqlite3.so')

    def prebuild_arch(self):
        super().prebuild_arch()
        mkdir._p.print(self.get_build_dir(self.arch) / 'jni')
        shutil.copyfile(self.resourcepath('Android.mk'), self.get_build_dir(self.arch) / 'jni' / 'Android.mk')

    def build_arch(self):
        super().build_arch()
        shutil.copyfile(self.get_build_dir(self.arch) / 'libs' / self.arch.name / 'libsqlite3.so', self.ctx.get_libs_dir(self.arch) / 'libsqlite3.so')

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        env['NDK_PROJECT_PATH'] = str(self.get_build_dir(arch))
        return env
