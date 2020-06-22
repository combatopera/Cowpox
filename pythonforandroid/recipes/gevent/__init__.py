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

import re
from pythonforandroid.logger import info
from pythonforandroid.recipe import CythonRecipe


class GeventRecipe(CythonRecipe):
    version = '1.4.0'
    url = 'https://pypi.python.org/packages/source/g/gevent/gevent-{version}.tar.gz'
    depends = ['librt', 'greenlet']
    patches = ["cross_compiling.patch"]

    def get_recipe_env(self, arch=None, with_flags_in_cc=True):
        """
        - Moves all -I<inc> -D<macro> from CFLAGS to CPPFLAGS environment.
        - Moves all -l<lib> from LDFLAGS to LIBS environment.
        - Copies all -l<lib> from LDLIBS to LIBS environment.
        - Fixes linker name (use cross compiler)  and flags (appends LIBS)
        """
        env = super().get_recipe_env(arch, with_flags_in_cc)
        # CFLAGS may only be used to specify C compiler flags, for macro definitions use CPPFLAGS
        regex = re.compile(r'(?:\s|^)-[DI][\S]+')
        env['CPPFLAGS'] = ''.join(re.findall(regex, env['CFLAGS'])).strip()
        env['CFLAGS'] = re.sub(regex, '', env['CFLAGS'])
        info('Moved "{}" from CFLAGS to CPPFLAGS.'.format(env['CPPFLAGS']))
        # LDFLAGS may only be used to specify linker flags, for libraries use LIBS
        regex = re.compile(r'(?:\s|^)-l[\w\.]+')
        env['LIBS'] = ''.join(re.findall(regex, env['LDFLAGS'])).strip()
        env['LIBS'] += ' {}'.format(''.join(re.findall(regex, env['LDLIBS'])).strip())
        env['LDFLAGS'] = re.sub(regex, '', env['LDFLAGS'])
        info('Moved "{}" from LDFLAGS to LIBS.'.format(env['LIBS']))
        return env


recipe = GeventRecipe()
