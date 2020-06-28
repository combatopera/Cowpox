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

from cowpox.config import Config
from cowpox.mirror import Mirror
from cowpox.platform import Platform
from cowpox.util import format_obj
from diapyr import types
from lagoon import cp, patch as patchexe, tar, touch, unzip
from pathlib import Path
from pkg_resources import resource_filename
from urllib.parse import urlparse
from zipfile import ZipFile
import hashlib, logging, os, shutil, subprocess

log = logging.getLogger(__name__)

class PluginType(type):

    def __init__(cls, *args):
        super().__init__(*args)
        fqmodule = cls.__module__
        cls.name = fqmodule[fqmodule.rfind('.') + 1:] # FIXME LATER: Do not override (possibly inherited) explicit name.

class Plugin(metaclass = PluginType): pass

class Context:

    @types()
    def __init__(self):
        pass

    def insitepackages(self, name):
        return False # TODO: Probably recreate site-packages if a dep has been rebuilt.

class Graph: pass

class GraphInfo: pass

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

    @property
    def dir_name(self):
        return self.name

    @types(Config, Context, Platform, Graph, Mirror, Arch, GraphInfo)
    def __init__(self, config, context, platform, graph, mirror, arch, graphinfo):
        self.other_builds = Path(config.other_builds)
        self.projectbuilddir = Path(config.build.dir)
        self.extroot = Path(config.container.extroot)
        self.context = context
        self.platform = platform
        self.graph = graph
        self.mirror = mirror
        self.arch = arch
        self.graphinfo = graphinfo

    def resourcepath(self, relpath):
        return Path(resource_filename(self.__module__, str(relpath)))

    def _extresourcepath(self, relpath):
        return Path(self.extroot, *self.__module__.split('.'), relpath)

    def apply_patch(self, relpath):
        log.info("Applying patch %s", relpath)
        patchexe._t._p1.print('-d', self.get_build_dir(), '-i', self.resourcepath(relpath))

    @property
    def buildcontainerparent(self):
        return self.other_builds / self.graphinfo.check_recipe_choices(self.name, [*self.depends, *([d] for d in self.opt_depends)])

    def get_build_container_dir(self):
        return self.buildcontainerparent / self.arch.builddirname()

    def get_build_dir(self):
        return self.get_build_container_dir() / self.dir_name

    def download_if_necessary(self):
        if self.url is None:
            log.debug("[%s] Skip download as no URL is set.", self.name)
            return
        if not urlparse(self.url).scheme:
            log.debug("[%s] Skip download as URL is a path.", self.name)
            return
        log.info("[%s] Downloading.", self.name)
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

    def prepare_build_dir(self):
        targetpath = self.get_build_dir()
        if self.url is None:
            log.debug("[%s] Skip unpack as no URL is set.", self.name)
            targetpath.mkdir()
            return
        if not urlparse(self.url).scheme:
            srcpath = Path(self.url.replace('/', os.sep))
            log.info("[%s] Copy from: %s", self.name, srcpath)
            # TODO: Copy without .git either.
            self._copywithoutbuild(srcpath if srcpath.is_absolute() else self._extresourcepath(srcpath), targetpath)
            return
        archivepath = self.mirror.getpath(self.url)
        log.info("[%s] Unpack for: %s", self.name, self.arch.name)
        # TODO LATER: Not such a good idea to use parent.
        # TODO LATER: Do not assume single top-level directory in archive.
        if self.url.endswith('.zip'):
            try:
                unzip.print(archivepath, cwd = targetpath.parent)
            except subprocess.CalledProcessError as e:
                if e.returncode not in {1, 2}:
                    raise
            with ZipFile(archivepath) as zf:
                rootname = zf.filelist[0].filename.split('/')[0]
        elif self.url.endswith(('.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz')):
            tar.xf.print(archivepath, cwd = targetpath.parent)
            rootname = tar.tf(archivepath).splitlines()[0].split('/')[0]
        else:
            raise Exception(f"Unsupported archive type: {self.url}")
        if rootname != targetpath.name:
            targetpath.with_name(rootname).rename(targetpath)

    def get_recipe_env(self):
        env = self.arch.get_env()
        build_platform, = (f"{uname.sysname}-{uname.machine}".lower() for uname in [os.uname()])
        env['BUILDLIB_PATH'] = self.graph.get_recipe(f"host{self.graph.python_recipe.name}").get_build_dir() / 'native-build' / 'build' / f"lib.{build_platform}-{self.graph.python_recipe.majminversion}"
        return env

    def prebuild(self):
        self.prebuild_arch()
        self.apply_patches()

    def prebuild_arch(self):
        pass

    def apply_patches(self):
        if self.patches:
            log.info("Applying patches for %s[%s]", self.name, self.arch.name)
            build_dir = self.get_build_dir()
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

    def mainbuild(self):
        self.build_arch()
        libs = [p for p in self._get_libraries() if p.name.endswith('.so')]
        if libs:
            cp.print(*libs, self.arch.libs_dir)

    def build_arch(self):
        pass

    def postbuild_arch(self):
        pass

    def _get_libraries(self):
        return {self.get_build_dir() / libpath for libpath in self.builtlibpaths}
