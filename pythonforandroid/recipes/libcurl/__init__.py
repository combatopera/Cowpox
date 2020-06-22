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

import sh
from pythonforandroid.recipe import Recipe
from pythonforandroid.util import current_directory
from pythonforandroid.logger import shprint
from os.path import join
from multiprocessing import cpu_count


class LibcurlRecipe(Recipe):
    version = '7.55.1'
    url = 'https://curl.haxx.se/download/curl-7.55.1.tar.gz'
    built_libraries = {'libcurl.so': 'dist/lib'}
    depends = ['openssl']

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)

        openssl_recipe = self.get_recipe('openssl', self.ctx)
        openssl_dir = openssl_recipe.get_build_dir(arch.arch)

        env['LDFLAGS'] += openssl_recipe.link_dirs_flags(arch)
        env['LIBS'] = env.get('LIBS', '') + openssl_recipe.link_libs_flags()

        with current_directory(self.get_build_dir(arch.arch)):
            dst_dir = join(self.get_build_dir(arch.arch), 'dist')
            shprint(
                sh.Command('./configure'),
                '--host=arm-linux-androideabi',
                '--enable-shared',
                '--with-ssl={}'.format(openssl_dir),
                '--prefix={}'.format(dst_dir),
                _env=env)
            shprint(sh.make, '-j', str(cpu_count()), _env=env)
            shprint(sh.make, 'install', _env=env)


recipe = LibcurlRecipe()
