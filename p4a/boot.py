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

from . import Arch, Graph, Plugin
from diapyr import types
from lagoon import cp, mv, rm, unzip
from pathlib import Path
from pkg_resources import resource_filename
from seizure.config import Config
from tempfile import TemporaryDirectory
import logging, os, shutil

log = logging.getLogger(__name__)

def _copy_files(src_root, dest_root, override):
    for root, dirnames, filenames in os.walk(src_root):
        root = Path(root)
        subdir = root.relative_to(src_root)
        for filename in filenames:
            dest_dir = (dest_root / subdir).mkdirp()
            src_file = root / filename
            dest_file = dest_dir / filename
            if src_file.is_file():
                if override and dest_file.exists():
                    dest_file.unlink()
                if not dest_file.exists():
                    shutil.copy(src_file, dest_file)
            else:
                dest_file.mkdirp()

class BootstrapType(type): pass

class Bootstrap(Plugin, metaclass = BootstrapType):

    contribroot = Path(resource_filename('pythonforandroid', '.'))
    recipe_depends = [("python2", "python3"), 'android']

    @types(Config, Graph, Arch)
    def __init__(self, config, graph, arch):
        self.bootstrap_dir = self.contribroot / 'bootstraps' / config.p4a.bootstrap
        self.buildsdir = Path(config.buildsdir)
        self.package_name = config.package.name
        self.android_api = config.android.api
        self.dist_dir = Path(config.dist_dir)
        self.build_dir = Path(config.bootstrap_builds, graph.check_recipe_choices(self.name, self.recipe_depends))
        self.javaclass_dir = config.javaclass_dir
        self.graph = graph
        self.arch = arch

    def prepare_dirs(self):
        _copy_files(self.bootstrap_dir / 'build', self.build_dir, True)
        _copy_files((self.bootstrap_dir / '..' / 'common').resolve() / 'build', self.build_dir, False)
        (self.build_dir / 'project.properties').write_text(f"target=android-{self.android_api}")
        self.dist_dir.mkdirp()

    def run_distribute(self, rctx):
        pass

    def distribute_libs(self, arch, src_dir):
        log.info('Copying libs')
        tgt_dir = (self.dist_dir / 'libs' / arch.name).mkdirp()
        for lib in src_dir.iterdir():
            cp._a.print(lib, tgt_dir)

    def distribute_javaclasses(self, dest_dir = 'src'):
        log.info('Copying java files')
        cp._a.print(self.javaclass_dir, (self.dist_dir / dest_dir).mkdirp())

    def distribute_aars(self, arch):
        log.info('Unpacking aars')
        for aar in (self.buildsdir / 'aars' / self.package_name).mkdirp().glob('*.aar'):
            self._unpack_aar(aar, arch)

    def _unpack_aar(self, aar, arch):
        with TemporaryDirectory() as temp_dir:
            name = os.path.splitext(aar.name)[0]
            jar_name = f"{name}.jar"
            log.info("unpack %s aar", name)
            log.debug("  from %s", aar)
            log.debug("  to %s", temp_dir)
            unzip._o.print(aar, '-d', temp_dir)
            jar_src = Path(temp_dir, 'classes.jar')
            jar_tgt = self.build_dir / 'libs' / jar_name
            log.debug("copy %s jar", name)
            log.debug("  from %s", jar_src)
            log.debug("  to %s", jar_tgt)
            libspath = (self.build_dir / 'libs').mkdirp()
            cp._a.print(jar_src, jar_tgt)
            so_src_dir = Path(temp_dir, 'jni', arch.name)
            so_tgt_dir = (libspath / arch.name).mkdirp()
            log.debug("copy %s .so", name)
            log.debug("  from %s", so_src_dir)
            log.debug("  to %s", so_tgt_dir)
            for f in so_src_dir.glob('*.so'):
                cp._a.print(f, so_tgt_dir)

    def fry_eggs(self, sitepackages):
        log.info("Frying eggs in %s", sitepackages)
        for rd in sitepackages.iterdir():
            if rd.is_dir() and rd.name.endswith('.egg'):
                log.info("  %s", rd.name)
                files = [f for f in rd.iterdir() if f.name != 'EGG-INFO']
                if files:
                    mv._t.print(sitepackages, *files)
                rm._rf.print(rd)
