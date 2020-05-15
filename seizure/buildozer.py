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

from .config import Config
from .dirs import Dirs
from diapyr import types
from os import walk
from os.path import splitext
from pathlib import Path
from shutil import copyfile, rmtree
import logging, os

log = logging.getLogger(__name__)

class Buildozer:

    @types(Config, Dirs)
    def __init__(self, config, dirs):
        self.config = config
        self.dirs = dirs

    def _copy_application_sources(self):
        source_dir = Path(self.config.getdefault('app', 'source.dir', '.')).resolve()
        include_exts = self.config.getlist('app', 'source.include_exts', '')
        log.debug('Copy application source from %s', source_dir)
        rmtree(self.dirs.app_dir)
        for root, dirs, files in walk(source_dir, followlinks=True):
            if True in [x.startswith('.') for x in root.split(os.sep)]:
                continue
            filtered_root = root[len(str(source_dir)) + 1:].lower()
            if filtered_root:
                filtered_root += '/'
            for fn in files:
                if fn.startswith('.'):
                    continue
                basename, ext = splitext(fn)
                if ext:
                    ext = ext[1:]
                    if include_exts and ext not in include_exts:
                        continue
                sfn = Path(root, fn)
                rfn = (self.dirs.app_dir / root[len(str(source_dir)) + 1:] / fn).resolve()
                rfn.parent.mkdir(parents = True, exist_ok = True)
                log.debug('Copy %s', sfn)
                copyfile(sfn, rfn)

    def _add_sitecustomize(self):
        copyfile(Path(__file__).parent / 'sitecustomize.py', self.dirs.app_dir / 'sitecustomize.py')
        main_py = self.dirs.app_dir / 'service' / 'main.py'
        if not main_py.exists():
            return
        header = (b'import sys, os; '
                   b'sys.path = [os.path.join(os.getcwd(),'
                   b'"..", "_applibs")] + sys.path\n')
        with open(main_py, 'rb') as fd:
            data = fd.read()
        data = header + data
        with open(main_py, 'wb') as fd:
            fd.write(data)
        log.info('Patched service/main.py to include applibs')
