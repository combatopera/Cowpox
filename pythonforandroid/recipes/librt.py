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

from os import makedirs, remove
from os.path import exists, join
import sh

from p4a import Recipe
from pythonforandroid.logger import shprint


class LibRt(Recipe):
    '''
    This is a dumb recipe. We may need this because some recipes inserted some
    flags `-lrt` without our control, case of:

        - :class:`~p4as.gevent.GeventRecipe`
        - :class:`~p4as.lxml.LXMLRecipe`

    .. note:: the librt doesn't exist in android but it is integrated into
        libc, so we create a symbolic link which we will remove when our build
        finishes'''

    @property
    def libc_path(self):
        return join(self.ctx.ndk_platform, 'usr', 'lib', 'libc')

    def build_arch(self, arch):
        # Create a temporary folder to add to link path with a fake librt.so:
        fake_librt_temp_folder = join(
            self.get_build_dir(arch.arch),
            "p4a-librt-recipe-tempdir"
        )
        if not exists(fake_librt_temp_folder):
            makedirs(fake_librt_temp_folder)

        # Set symlinks, and make sure to update them on every build run:
        if exists(join(fake_librt_temp_folder, "librt.so")):
            remove(join(fake_librt_temp_folder, "librt.so"))
        shprint(sh.ln, '-sf',
                self.libc_path + '.so',
                join(fake_librt_temp_folder, "librt.so"),
                )
        if exists(join(fake_librt_temp_folder, "librt.a")):
            remove(join(fake_librt_temp_folder, "librt.a"))
        shprint(sh.ln, '-sf',
                self.libc_path + '.a',
                join(fake_librt_temp_folder, "librt.a"),
               )

        # Add folder as -L link option for all recipes if not done yet:
        if fake_librt_temp_folder not in arch.extra_global_link_paths:
            arch.extra_global_link_paths.append(
                fake_librt_temp_folder
            )


recipe = LibRt()
