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

from . import Arch
from .config import Config
from .mirror import Mirror
from .platform import Platform
from .util import Plugin
from diapyr import types
from lagoon import patch, tar, unzip
from pathlib import Path
from pkg_resources import resource_filename
from urllib.parse import urlparse
from zipfile import ZipFile
import hashlib, logging, os, shutil, subprocess

log = logging.getLogger(__name__)

class Recipe(Plugin):

    md5sum = None
    depends = []
    '''A list containing the names of any recipes that this recipe depends on.
    '''

    conflicts = []
    '''A list containing the names of any recipes that are known to be
    incompatible with this one.'''

    opt_depends = []
    '''A list of optional dependencies, that must be built before this
    recipe if they are built at all, but whose presence is not essential.'''
    python_depends = []
    '''A list of pure-Python packages that this package requires. These
    packages will NOT be available at build time, but will be added to the
    list of pure-Python packages to install via pip. If you need these packages
    at build time, you must create a recipe.'''

    @classmethod
    def get_opt_depends_in_list(cls, recipenames):
        return [name for name in recipenames if name in cls.opt_depends]

    @types(Config, Platform, Mirror, Arch)
    def __init__(self, config, platform, mirror, arch):
        self.recipebuilddir = Path(config.builds.dir, self.name)
        self.projectbuilddir = Path(config.build.dir)
        self.extroot = Path(config.container.extroot)
        self.platform = platform
        self.mirror = mirror
        self.arch = arch

    def resourcepath(self, relpath):
        return Path(resource_filename(self.__module__, str(relpath)))

    def _extresourcepath(self, relpath):
        return Path(self.extroot, *self.__module__.split('.'), relpath)

    def apply_patches(self, *relpaths):
        for relpath in relpaths:
            log.info("Apply patch: %s", relpath)
            patch._t._p1.print('-d', self.recipebuilddir, '-i', self.resourcepath(relpath))

    def _copywithoutbuild(self, frompath, topath):
        try:
            frompath.relative_to(self.projectbuilddir)
        except ValueError:
            try:
                self.projectbuilddir.relative_to(frompath)
            except ValueError:
                ignore = None
            else:
                def ignore(dirpath, _):
                    if Path(dirpath) == self.projectbuilddir.parent:
                        log.debug("Not copying: %s", self.projectbuilddir)
                        return [self.projectbuilddir.name]
                    return []
            shutil.copytree(frompath, topath, ignore = ignore)
        else:
            log.warning("Refuse to copy %s descendant: %s", self.projectbuilddir, frompath)

    def _prepare(self):
        if self.url is None:
            log.debug("[%s] Skip unpack as no URL is set.", self.name)
            self.recipebuilddir.mkdir()
            return
        if not urlparse(self.url).scheme:
            srcpath = Path(self.url.replace('/', os.sep))
            log.info("[%s] Copy from: %s", self.name, srcpath)
            # TODO: Copy without .git either.
            self._copywithoutbuild(srcpath if srcpath.is_absolute() else self._extresourcepath(srcpath), self.recipebuilddir)
            return
        log.info("[%s] Downloading.", self.name)
        archivepath = self.mirror.download(self.url)
        if self.md5sum is not None:
            current_md5 = hashlib.md5(archivepath.read_bytes()).hexdigest()
            if current_md5 != self.md5sum:
                log.debug("Generated md5sum: %s", current_md5)
                log.debug("Expected md5sum: %s", self.md5sum)
                raise ValueError(f"Generated md5sum does not match expected md5sum for {self.name} recipe")
            log.debug("[%s] MD5 OK.", self.name)
        log.info("[%s] Unpack for: %s", self.name, self.arch.name)
        # TODO LATER: Not such a good idea to use parent.
        # TODO LATER: Do not assume single top-level directory in archive.
        if self.url.endswith('.zip'):
            try:
                unzip.print(archivepath, cwd = self.recipebuilddir.parent)
            except subprocess.CalledProcessError as e:
                if e.returncode not in {1, 2}:
                    raise
            with ZipFile(archivepath) as zf:
                rootname = zf.filelist[0].filename.split('/')[0]
        elif self.url.endswith(('.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz')):
            tar.xf.print(archivepath, cwd = self.recipebuilddir.parent)
            rootname = tar.tf(archivepath).splitlines()[0].split('/')[0]
        else:
            raise Exception(f"Unsupported archive type: {self.url}")
        if rootname != self.recipebuilddir.name:
            self.recipebuilddir.with_name(rootname).rename(self.recipebuilddir)

    def makerecipe(self, make):
        def target():
            self._prepare()
            self.mainbuild()
            self.arch.strip_object_files(self.recipebuilddir) # TODO: CythonRecipe also does this.
        return make(self.recipebuilddir, self.platform.memo, target) # FIXME: Some recipes depend on others.

class BootstrapNDKRecipe(Recipe):

    @types()
    def __init(self):
        self.jni_dir = self.recipebuilddir / 'jni'

    def ndk_build(self, env):
        self.platform.ndk_build.print(env = env, cwd = self.jni_dir)

class NDKRecipe(Recipe):

    @types(Config)
    def __init(self, config):
        self.ndk_api = config.android.ndk_api

    def get_lib_dir(self):
        return self.recipebuilddir / 'obj' / 'local' / self.arch.name

    def ndk_build(self, env):
        # XXX: Can the make variables go in the env?
        self.platform.ndk_build.print(f"APP_PLATFORM=android-{self.ndk_api}", f"APP_ABI={self.arch.name}", env = env, cwd = self.recipebuilddir)
