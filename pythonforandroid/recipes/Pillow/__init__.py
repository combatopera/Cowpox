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

from pythonforandroid.recipe import CompiledComponentsPythonRecipe
from os.path import join


class PillowRecipe(CompiledComponentsPythonRecipe):

    version = '7.0.0'
    url = 'https://github.com/python-pillow/Pillow/archive/{version}.tar.gz'
    site_packages_name = 'Pillow'
    depends = ['png', 'jpeg', 'freetype', 'setuptools']
    patches = [join('patches', 'fix-setup.patch')]

    call_hostpython_via_targetpython = False

    def get_recipe_env(self, arch=None, with_flags_in_cc=True):
        env = super(PillowRecipe, self).get_recipe_env(arch, with_flags_in_cc)

        env['ANDROID_ROOT'] = join(self.ctx.ndk_platform, 'usr')
        ndk_lib_dir = join(self.ctx.ndk_platform, 'usr', 'lib')
        ndk_include_dir = join(self.ctx.ndk_dir, 'sysroot', 'usr', 'include')

        png = self.get_recipe('png', self.ctx)
        png_lib_dir = join(png.get_build_dir(arch.arch), '.libs')
        png_inc_dir = png.get_build_dir(arch)

        jpeg = self.get_recipe('jpeg', self.ctx)
        jpeg_inc_dir = jpeg_lib_dir = jpeg.get_build_dir(arch.arch)

        freetype = self.get_recipe('freetype', self.ctx)
        free_lib_dir = join(freetype.get_build_dir(arch.arch), 'objs', '.libs')
        free_inc_dir = join(freetype.get_build_dir(arch.arch), 'include')

        # harfbuzz is a direct dependency of freetype and we need the proper
        # flags to successfully build the Pillow recipe, so we add them here.
        harfbuzz = self.get_recipe('harfbuzz', self.ctx)
        harf_lib_dir = join(harfbuzz.get_build_dir(arch.arch), 'src', '.libs')
        harf_inc_dir = harfbuzz.get_build_dir(arch.arch)

        env['JPEG_ROOT'] = '{}|{}'.format(jpeg_lib_dir, jpeg_inc_dir)
        env['FREETYPE_ROOT'] = '{}|{}'.format(free_lib_dir, free_inc_dir)
        env['ZLIB_ROOT'] = '{}|{}'.format(ndk_lib_dir, ndk_include_dir)

        cflags = ' -I{}'.format(png_inc_dir)
        cflags += ' -I{} -I{}'.format(harf_inc_dir, join(harf_inc_dir, 'src'))
        cflags += ' -I{}'.format(free_inc_dir)
        cflags += ' -I{}'.format(jpeg_inc_dir)
        cflags += ' -I{}'.format(ndk_include_dir)

        env['LIBS'] = ' -lpng -lfreetype -lharfbuzz -ljpeg -lturbojpeg'

        env['LDFLAGS'] += ' -L{} -L{} -L{} -L{}'.format(
            png_lib_dir, harf_lib_dir, jpeg_lib_dir, ndk_lib_dir)
        if cflags not in env['CFLAGS']:
            env['CFLAGS'] += cflags
        return env


recipe = PillowRecipe()
