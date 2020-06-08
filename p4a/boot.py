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

from lagoon import cp, find, mv, rm, unzip
from lagoon.program import Program
from pathlib import Path
from tempfile import TemporaryDirectory
import logging, os, shlex, shutil, subprocess

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

class Bootstrap:

    name = ''
    jni_subdir = '/jni'
    ctx = None
    recipe_depends = [("python2", "python3"), 'android']

    @property
    def dist_dir(self):
        return self.distribution.dist_dir

    @property
    def jni_dir(self):
        return self.name + self.jni_subdir

    def get_build_dir(self):
        return self.ctx.buildsdir / 'bootstrap_builds' / self.ctx.check_recipe_choices(self.name, self.recipe_depends)

    def get_dist_dir(self, name):
        return self.ctx.distsdir / name

    @property
    def name(self):
        modname = self.__class__.__module__
        return modname.split(".", 2)[-1]

    def prepare_build_dir(self):
        '''Ensure that a build dir exists for the recipe. This same single
        dir will be used for building all different archs.'''
        self.build_dir = self.get_build_dir()
        _copy_files(self.bootstrap_dir / 'build', self.build_dir, True)
        _copy_files((self.bootstrap_dir / ".." / 'common').resolve() / 'build', self.build_dir, False)
        (self.build_dir / 'project.properties').write_text(f"target=android-{self.ctx.android_api}")

    def prepare_dist_dir(self):
        self.dist_dir.mkdirp()

    def run_distribute(self):
        self.distribution.save_info()

    def distribute_libs(self, arch, src_dir):
        log.info('Copying libs')
        tgt_dir = (self.dist_dir / 'libs' / arch.name).mkdirp()
        for lib in src_dir.iterdir():
            cp._a.print(lib, tgt_dir)

    def distribute_javaclasses(self, javaclass_dir, dest_dir = 'src'):
        log.info('Copying java files')
        if javaclass_dir.exists():
            cp._a.print(javaclass_dir, (self.dist_dir / dest_dir).mkdirp())

    def distribute_aars(self, arch):
        log.info('Unpacking aars')
        for aar in self.ctx.aars_dir.glob('*.aar'):
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

    def strip_libraries(self, arch):
        log.info('Stripping libraries')
        env = arch.get_env(self.ctx)
        tokens = shlex.split(env['STRIP'])
        strip = Program.text(self.ctx.ndk_dir / 'toolchains' / f"{self.ctx.toolchain_prefix}-{self.ctx.toolchain_version}" / 'prebuilt' / 'linux-x86_64' / 'bin' / tokens[0]).partial(*tokens[1:])
        libs_dir = self.dist_dir / '_python_bundle' / '_python_bundle' / 'modules'
        filens = find(libs_dir, self.dist_dir / 'libs', '-iname', '*.so').splitlines()
        log.info('Stripping libraries in private dir')
        for filen in filens:
            try:
                strip.print(filen, env = env)
            except subprocess.CalledProcessError as e:
                if 1 != e.returncode:
                    raise
                log.debug("Failed to strip %s", filen)

    def fry_eggs(self, sitepackages):
        log.info("Frying eggs in %s", sitepackages)
        for rd in sitepackages.iterdir():
            if rd.is_dir() and rd.name.endswith('.egg'):
                log.info("  %s", rd.name)
                files = [f for f in rd.iterdir() if f.name != 'EGG-INFO']
                if files:
                    mv._t.print(sitepackages, *files)
                rm._rf.print(rd)
