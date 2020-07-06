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

from . import Arch, BootstrapOK, GraphInfo, InterpreterRecipe, JavaSrc, RecipesOK, PipInstallOK, SkeletonOK
from .config import Config
from .util import mergetree, Plugin, PluginType, writeproperties
from diapyr import types
from lagoon import cp, unzip
from pathlib import Path
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

class BootstrapType(PluginType): pass

class Bootstrap(Plugin, metaclass = BootstrapType):

    MIN_TARGET_API = 26
    recipe_depends = 'python3', 'android'

    @types(Config, Arch, GraphInfo)
    def __init__(self, config, arch, graphinfo):
        self.common_dir = Path(config.bootstrap.common.dir)
        self.bootstrap_dir = Path(config.bootstrap.dir)
        self.buildsdir = Path(config.buildsdir)
        self.package_name = config.package.name
        self.android_api = config.android.api
        if self.android_api < self.MIN_TARGET_API:
            log.warning("Target API %s < %s", self.android_api, self.MIN_TARGET_API)
            log.warning('Target APIs lower than 26 are no longer supported on Google Play, and are not recommended. Note that the Target API can be higher than your device Android version, and should usually be as high as possible.')
        self.android_project_dir = Path(config.android.project.dir)
        self.android_project_libs = Path(config.android.project.jniLibs)
        self.build_dir = Path(config.bootstrap_builds, graphinfo.check_recipe_choices(self.name, self.recipe_depends))
        self.sdk_dir = config.SDK.dir
        self.arch = arch
        self.graphinfo = graphinfo

    def templatepath(self, relpath):
        relpath = Path('templates', relpath)
        path = self.bootstrap_dir / relpath
        return path if path.exists() else self.common_dir / relpath

    @types(this = SkeletonOK)
    def prepare_dirs(self):
        _copy_files(self.bootstrap_dir, self.build_dir, True)
        _copy_files(self.common_dir, self.build_dir, False)

    @types(InterpreterRecipe, [JavaSrc], RecipesOK, PipInstallOK, this = BootstrapOK) # XXX: What does this really depend on?
    def toandroidproject(self, interpreterrecipe, javasrcs, *_):
        self.arch.strip_object_files(self.buildsdir) # XXX: What exactly does this do?
        shutil.copytree(self.build_dir, self.android_project_dir) # FIXME: Next thing to make incremental.
        writeproperties(self.android_project_dir / 'project.properties', target = f"android-{self.android_api}")
        writeproperties(self.android_project_dir / 'local.properties', **{'sdk.dir': self.sdk_dir}) # Required by gradle build.
        log.info('Copying libs.')
        mergetree(self.build_dir / 'libs', self.android_project_libs)
        mergetree(self.arch.libs_dir, self.android_project_libs / self.arch.name)
        self._distribute_aars()
        shutil.copy2(interpreterrecipe.androidbuild / interpreterrecipe.instsoname, (self.android_project_libs / self.arch.name).mkdirp())
        self.arch.striplibs(self.android_project_libs)
        for javasrc in javasrcs:
            self._distribute_javaclasses(javasrc.javasrc)

    def _distribute_javaclasses(self, javaclass_dir):
        log.info("Copying java files from: %s", javaclass_dir)
        mergetree(javaclass_dir, self.android_project_dir / 'src' / 'main' / 'java')

    def _distribute_aars(self):
        log.info('Unpacking aars')
        for aar in (self.buildsdir / 'aars' / self.package_name).glob('*.aar'): # TODO LATER: Configure these a different way.
            self._unpack_aar(aar)

    def _unpack_aar(self, aar):
        with TemporaryDirectory() as temp_dir:
            name = os.path.splitext(aar.name)[0]
            jar_name = f"{name}.jar"
            log.info("unpack %s aar", name)
            log.debug("  from %s", aar)
            log.debug("  to %s", temp_dir)
            unzip._o.print(aar, '-d', temp_dir)
            jar_src = Path(temp_dir, 'classes.jar')
            jar_tgt = self.android_project_libs.mkdirp() / jar_name
            log.debug("copy %s jar", name)
            log.debug("  from %s", jar_src)
            log.debug("  to %s", jar_tgt)
            cp._a.print(jar_src, jar_tgt)
            so_src_dir = Path(temp_dir, 'jni', self.arch.name)
            so_tgt_dir = (self.android_project_libs / self.arch.name).mkdirp()
            log.debug("copy %s .so", name)
            log.debug("  from %s", so_src_dir)
            log.debug("  to %s", so_tgt_dir)
            for f in so_src_dir.glob('*.so'):
                cp._a.print(f, so_tgt_dir)
