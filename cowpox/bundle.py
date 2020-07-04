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

from . import Arch, BootstrapOK, BundleOK, PythonBundle
from .config import Config
from .make import Make
from .pyrecipe import PythonRecipe
from .python import GuestPythonRecipe
from diapyr import types
from fnmatch import fnmatch
from lagoon import mv, rm, zip
from pathlib import Path
import logging, os, shutil

log = logging.getLogger(__name__)

class PythonBundleImpl(PythonBundle):

    stdlib_dir_blacklist = {
        '__pycache__',
        'test',
        'tests',
        'lib2to3',
        'ensurepip',
        'idlelib',
        'tkinter',
    }
    stdlib_filen_blacklist = [
        '*.py',
        '*.exe',
        '*.whl',
    ]
    site_packages_dir_blacklist = {
        '__pycache__',
        'tests',
    }
    site_packages_filen_blacklist = [
        '*.py',
    ]

    @staticmethod
    def _walk_valid_filens(base_dir, invalid_dir_names, invalid_file_patterns):
        for dirn, subdirs, filens in os.walk(base_dir):
            for i in reversed(range(len(subdirs))):
                subdir = subdirs[i]
                if subdir in invalid_dir_names:
                    subdirs.pop(i)
            for filen in filens:
                for pattern in invalid_file_patterns:
                    if fnmatch(filen, pattern):
                        break
                else:
                    yield Path(dirn, filen)

    @types(Config, Arch, GuestPythonRecipe, [PythonRecipe])
    def __init__(self, config, arch, pythonrecipe, recipes):
        self.bundledir = Path(config.bundledir)
        self.arch = arch
        self.pythonrecipe = pythonrecipe
        self.recipes = recipes

    @types(Make, BootstrapOK, this = BundleOK) # XXX: Does this really depend on BootstrapOK?
    def create_python_bundle(self, make, _):
        make(self._createbundle)

    def _createbundle(self):
        yield self.bundledir
        modules_dir = (self.bundledir / 'modules').mkdirp()
        log.info("Copy %s files into the bundle", len(self.pythonrecipe.module_filens))
        for filen in self.pythonrecipe.module_filens:
            log.debug(" - copy %s", filen)
            shutil.copy2(filen, modules_dir)
        self.arch.striplibs(modules_dir)
        stdlib_filens = list(self._walk_valid_filens(self.pythonrecipe.stdlibdir, self.stdlib_dir_blacklist, self.stdlib_filen_blacklist))
        log.info("Zip %s files into the bundle", len(stdlib_filens))
        zip.print(self.bundledir / 'stdlib.zip', *(p.relative_to(self.pythonrecipe.stdlibdir) for p in stdlib_filens), cwd = self.pythonrecipe.stdlibdir)
        sitepackagesdir = (self.bundledir / 'site-packages').mkdirp()
        for recipe in self.recipes:
            filens = list(self._walk_valid_filens(recipe.bundlepackages, self.site_packages_dir_blacklist, self.site_packages_filen_blacklist))
            log.info("Copy %s files into the site-packages", len(filens))
            for filen in filens:
                log.debug(" - copy %s", filen)
                shutil.copy2(filen, (sitepackagesdir / filen.relative_to(recipe.bundlepackages)).pmkdirp())
        log.info('Renaming .so files to reflect cross-compile')
        self._reduce_object_file_names(sitepackagesdir)
        log.info("Frying eggs in: %s", sitepackagesdir)
        for rd in sitepackagesdir.iterdir():
            if rd.is_dir() and rd.name.endswith('.egg'):
                log.debug("Egg: %s", rd.name)
                files = [f for f in rd.iterdir() if f.name != 'EGG-INFO']
                if files:
                    mv._t.print(sitepackagesdir, *files)
                rm._rf.print(rd)

    def _reduce_object_file_names(self, dirn):
        """Recursively renames all files named YYY.cpython-...-linux-gnu.so"
        to "YYY.so", i.e. removing the erroneous architecture name
        coming from the local system.
        """
        for filen in dirn.rglob('*.so'):
            parts = filen.name.split('.')
            if len(parts) > 2:
                mv.print(filen, filen.parent / f"{parts[0]}.so")
