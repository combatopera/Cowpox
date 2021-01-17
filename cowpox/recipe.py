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
from .mirror import Mirror
from .platform import Platform
from aridity.config import Config
from diapyr import types
from lagoon import patch, tar, unzip
from pathlib import Path
from zipfile import ZipFile
import hashlib, logging, shutil, subprocess

log = logging.getLogger(__name__)

class Recipe:

    depends = ()

    @types(Config, Platform, Mirror, Arch)
    def __init__(self, config, platform, mirror, arch):
        self.recipebuilddir = Path(config.builds.dir, self.name)
        self.projectbuilddir = Path(config.build.dir)
        self.extroot = Path(config.container.extroot)
        self.recipe_patch_dir = Path(config.patch.dir, self.name) # XXX: Or use normalised name?
        self.platform = platform
        self.mirror = mirror
        self.arch = arch

    def apply_patches(self, *relpaths):
        for relpath in relpaths:
            log.info("Apply patch: %s", relpath)
            patch._t._p1[print]('-d', self.recipebuilddir, '-i', self.recipe_patch_dir / relpath)

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
            shutil.copytree(frompath, topath, symlinks = True, ignore = ignore)
        else:
            log.warning("Refuse to copy %s descendant: %s", self.projectbuilddir, frompath)

    def preparedirlocal(self, srcpath):
        log.info("[%s] Copy from: %s", self.name, srcpath)
        # TODO: Copy without .git either.
        self._copywithoutbuild(srcpath, self.recipebuilddir)

    def preparedir(self, url, md5sum = None):
        log.info("[%s] Downloading.", self.name)
        archivepath = self.mirror.download(url)
        if md5sum is not None:
            current_md5 = hashlib.md5(archivepath.read_bytes()).hexdigest()
            if current_md5 != md5sum:
                log.debug("Generated md5sum: %s", current_md5)
                log.debug("Expected md5sum: %s", md5sum)
                raise ValueError(f"Generated md5sum does not match expected md5sum for {self.name} recipe")
            log.debug("[%s] MD5 OK.", self.name)
        log.info("[%s] Unpack for: %s", self.name, self.arch.name)
        # TODO LATER: Not such a good idea to use parent.
        # TODO LATER: Do not assume single top-level directory in archive.
        if url.endswith('.zip'):
            try:
                unzip[print](archivepath, cwd = self.recipebuilddir.parent)
            except subprocess.CalledProcessError as e:
                if e.returncode not in {1, 2}:
                    raise
            with ZipFile(archivepath) as zf:
                rootname = zf.filelist[0].filename.split('/')[0]
        elif url.endswith(('.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz')):
            tar.xf[print](archivepath, cwd = self.recipebuilddir.parent)
            rootname = tar.tf(archivepath).splitlines()[0].split('/')[0]
        else:
            raise Exception(f"Unsupported archive type: {url}")
        if rootname != self.recipebuilddir.name:
            self.recipebuilddir.with_name(rootname).rename(self.recipebuilddir)

    def striplibs(self):
        self.arch.striplibs(self.recipebuilddir)

class BootstrapNDKRecipe(Recipe):

    @types()
    def __init(self):
        self.jni_dir = self.recipebuilddir / 'jni'

    def ndk_build(self, env):
        self.platform.ndk_build[print](env = env, cwd = self.jni_dir)
        self.striplibs()

class NDKRecipe(Recipe):

    @types(Config)
    def __init(self, config):
        self.ndk_api = config.android.ndk_api
        self.jni_dir = self.recipebuilddir / 'jni'

    def get_lib_dir(self):
        return self.recipebuilddir / 'obj' / 'local' / self.arch.name

    def ndk_build(self, env):
        # TODO: These look like Application.mk variables.
        self.platform.ndk_build[print](f"APP_PLATFORM=android-{self.ndk_api}", f"APP_ABI={self.arch.name}", env = env, cwd = self.recipebuilddir)
        self.striplibs()
