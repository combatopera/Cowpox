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

from . import Arch, BootstrapOK, GraphInfo, InterpreterRecipe, RecipesOK, PipInstallOK, SkeletonOK
from .config import Config
from .util import mergetree, Plugin, PluginType
from diapyr import types
from pathlib import Path
import logging, shutil

log = logging.getLogger(__name__)

class BootstrapType(PluginType): pass

class Bootstrap(Plugin, metaclass = BootstrapType):

    MIN_TARGET_API = 26
    recipe_depends = 'python3', 'android'

    @types(Config, Arch, GraphInfo)
    def __init__(self, config, arch, graphinfo):
        self.common_dir = Path(config.bootstrap.common.dir)
        self.bootstrap_dir = Path(config.bootstrap.dir)
        self.buildsdir = Path(config.buildsdir)
        android_api = config.android.api
        if android_api < self.MIN_TARGET_API:
            log.warning("Target API %s < %s", android_api, self.MIN_TARGET_API)
            log.warning('Target APIs lower than 26 are no longer supported on Google Play, and are not recommended. Note that the Target API can be higher than your device Android version, and should usually be as high as possible.')
        self.android_project_dir = Path(config.android.project.dir)
        self.build_dir = Path(config.bootstrap_builds, graphinfo.check_recipe_choices(self.name, self.recipe_depends))
        self.arch = arch
        self.graphinfo = graphinfo

    def templatepath(self, relpath):
        relpath = Path('templates', relpath)
        path = self.bootstrap_dir / relpath
        return path if path.exists() else self.common_dir / relpath

    @types(this = SkeletonOK)
    def prepare_dirs(self):
        mergetree(self.bootstrap_dir, self.build_dir)
        mergetree(self.common_dir, self.build_dir, True)

    @types(InterpreterRecipe, RecipesOK, PipInstallOK, this = BootstrapOK) # XXX: What does this really depend on?
    def toandroidproject(self, interpreterrecipe, *_):
        self.arch.strip_object_files(self.buildsdir) # XXX: What exactly does this do?
        shutil.copytree(self.build_dir, self.android_project_dir) # FIXME: Next thing to make incremental.
