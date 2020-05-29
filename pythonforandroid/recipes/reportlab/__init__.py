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

from pythonforandroid.logger import shprint
from p4a import CompiledComponentsPythonRecipe
from pathlib import Path
import logging, os, sh

log = logging.getLogger(__name__)

class ReportLabRecipe(CompiledComponentsPythonRecipe):

    version = 'c088826211ca'
    url = 'https://bitbucket.org/rptlab/reportlab/get/{version}.tar.gz'
    depends = ['freetype']
    call_hostpython_via_targetpython = False

    def prebuild_arch(self, arch):
        if not self.is_patched(arch):
            super(ReportLabRecipe, self).prebuild_arch(arch)
            recipe_dir = self.get_build_dir(arch.arch)
            # Some versions of reportlab ship with a GPL-licensed font.
            # Remove it, since this is problematic in .apks unless the
            # entire app is GPL:
            font_dir = os.path.join(recipe_dir,
                                    "src", "reportlab", "fonts")
            if os.path.exists(font_dir):
                for l in os.listdir(font_dir):
                    if l.lower().startswith('darkgarden'):
                        os.remove(os.path.join(font_dir, l))
            # Apply patches:
            self.apply_patch('patches/fix-setup.patch', arch.arch)
            shprint(sh.touch, os.path.join(recipe_dir, '.patched'))
            ft = self.get_recipe('freetype')
            ft_dir = ft.get_build_dir(arch.arch)
            ft_lib_dir = os.environ.get('_FT_LIB_', os.path.join(ft_dir, 'objs', '.libs'))
            ft_inc_dir = os.environ.get('_FT_INC_', os.path.join(ft_dir, 'include'))
            tmp_dir = os.path.normpath(os.path.join(recipe_dir, "..", "..", "tmp"))
            log.info("reportlab recipe: recipe_dir=%s", recipe_dir)
            log.info("reportlab recipe: tmp_dir=%s", tmp_dir)
            log.info("reportlab recipe: ft_dir=%s", ft_dir)
            log.info("reportlab recipe: ft_lib_dir=%s", ft_lib_dir)
            log.info("reportlab recipe: ft_inc_dir=%s", ft_inc_dir)
            with self.current_directory(recipe_dir):
                Path(tmp_dir).mkdirp()
                pfbfile = os.path.join(tmp_dir, "pfbfer-20070710.zip")
                if not os.path.isfile(pfbfile):
                    sh.wget("http://www.reportlab.com/ftp/pfbfer-20070710.zip", "-O", pfbfile)
                sh.unzip("-u", "-d", os.path.join(recipe_dir, "src", "reportlab", "fonts"), pfbfile)
                if os.path.isfile("setup.py"):
                    with open('setup.py', 'r') as f:
                        text = f.read().replace('_FT_LIB_', ft_lib_dir).replace('_FT_INC_', ft_inc_dir)
                    with open('setup.py', 'w') as f:
                        f.write(text)

