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

from diapyr import types
from lagoon import cp, mv, patch as patchexe, rm, tar, touch, unzip
from pathlib import Path
from pkg_resources import resource_filename
from seizure.config import Config
from seizure.mirror import Mirror
from seizure.platform import Platform
from seizure.util import format_obj
from urllib.parse import urlparse
from zipfile import ZipFile
import hashlib, logging, os, shutil, subprocess

log = logging.getLogger(__name__)

class Plugin:

    @property
    def name(self):
        fqmodule = self._fqmodulename()
        return fqmodule[fqmodule.rfind('.') + 1:]

    def _fqmodulename(self):
        return type(self).__module__

class Context: pass

class Graph: pass

class Arch: pass

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
    patches = ()
    python_depends = []
    '''A list of pure-Python packages that this package requires. These
    packages will NOT be available at build time, but will be added to the
    list of pure-Python packages to install via pip. If you need these packages
    at build time, you must create a recipe.'''
    builtlibpaths = ()

    @classmethod
    def get_opt_depends_in_list(cls, recipenames):
        return [name for name in recipenames if name in cls.opt_depends]

    @property
    def url(self):
        return format_obj(self.urlformat, self)

    @types(Config, Context, Platform, Graph, Mirror, Arch)
    def __init__(self, config, context, platform, graph, mirror, arch):
        self.other_builds = Path(config.other_builds)
        self.projectbuilddir = Path(config.build.dir)
        self.ctx = context
        self.platform = platform
        self.graph = graph
        self.mirror = mirror
        self.arch = arch

    def resourcepath(self, relpath):
        return Path(resource_filename(self._fqmodulename(), str(relpath)))

    def apply_patch(self, relpath):
        log.info("Applying patch %s", relpath)
        patchexe._t._p1.print('-d', self.get_build_dir(self.arch), '-i', self.resourcepath(relpath))

    def get_build_container_dir(self, arch):
        return self.other_builds / self.graph.check_recipe_choices(self.name, [*self.depends, *([d] for d in self.opt_depends)]) / arch.builddirname()

    def get_build_dir(self, arch):
        return self.get_build_container_dir(arch) / self.name

    def download_if_necessary(self):
        log.info("Downloading %s", self.name)
        if self.url is None or not urlparse(self.url).scheme:
            log.info("Skipping %s download as no URL is set", self.name)
            return
        path = self.mirror.download(self.url)
        if self.md5sum is not None:
            current_md5 = hashlib.md5(path.read_bytes()).hexdigest()
            if current_md5 != self.md5sum:
                log.debug("Generated md5sum: %s", current_md5)
                log.debug("Expected md5sum: %s", self.md5sum)
                raise ValueError(f"Generated md5sum does not match expected md5sum for {self.name} recipe")
            log.debug("[%s] MD5 OK.", self.name)

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

    def _unpack(self):
        directory_name = self.get_build_dir(self.arch)
        if self.url is not None and not urlparse(self.url).scheme:
            srcpath = Path(self.url.replace('/', os.sep))
            rm._rf.print(directory_name)
            self._copywithoutbuild(srcpath if srcpath.is_absolute() else self.resourcepath(srcpath), directory_name)
            return
        log.info("Unpacking %s for %s", self.name, self.arch.name)
        build_dir = self.get_build_container_dir(self.arch)
        if self.url is None:
            log.info("Skipping %s unpack as no URL is set", self.name)
            return
        if not directory_name.is_dir():
            extraction_filename = self.mirror.getpath(self.url)
            if self.url.endswith('.zip'):
                try:
                    unzip.print(extraction_filename, cwd = build_dir)
                except subprocess.CalledProcessError as e:
                    # return code 1 means unzipping had
                    # warnings but did complete,
                    # apparently happens sometimes with
                    # github zips
                    if e.returncode not in {1, 2}:
                        raise
                zf = ZipFile(extraction_filename, 'r')
                root_directory = zf.filelist[0].filename.split('/')[0]
                if root_directory != directory_name.name:
                    mv.print(root_directory, directory_name, cwd = build_dir)
            elif self.url.endswith(('.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz')):
                tar.xf.print(extraction_filename, cwd = build_dir)
                root_directory = tar.tf(extraction_filename).split('\n')[0].split('/')[0]
                if root_directory != directory_name.name:
                    mv.print(root_directory, directory_name, cwd = build_dir)
            else:
                raise Exception(f"Could not extract {extraction_filename} download, it must be .zip, .tar.gz or .tar.bz2 or .tar.xz")
        else:
            log.info("%s is already unpacked, skipping", self.name)

    def get_recipe_env(self, arch):
        return arch.get_env()

    def prebuild_arch(self):
        pass

    def apply_patches(self):
        if self.patches:
            log.info("Applying patches for %s[%s]", self.name, self.arch.name)
            build_dir = self.get_build_dir(self.arch)
            if (build_dir / '.patched').exists():
                log.info("%s already patched, skipping", self.name)
                return
            for patch in self.patches:
                while True:
                    try:
                        acceptrecipe = patch.acceptrecipe
                    except AttributeError:
                        self.apply_patch(patch)
                        break
                    nextpatch = acceptrecipe(self)
                    if nextpatch is None:
                        log.debug("Patch denied: %s", patch)
                        break
                    patch = nextpatch
            touch.print(build_dir / '.patched')

    def should_build(self):
        return not self.builtlibpaths or not all(p.exists() for p in self._get_libraries()) # XXX: Weird logic?

    def build_arch(self):
        pass

    def install_libraries(self):
        libs = [p for p in self._get_libraries() if p.name.endswith('.so')]
        if libs:
            cp.print(*libs, self.arch.libs_dir)

    def postbuild_arch(self):
        pass

    def prepare_build_dir(self):
        self.get_build_container_dir(self.arch).mkdirp()
        self._unpack()

    def has_libs(self, *libs):
        return all(map(self.arch.has_lib, libs))

    def _get_libraries(self):
        return {self.get_build_dir(self.arch) / libpath for libpath in self.builtlibpaths}
