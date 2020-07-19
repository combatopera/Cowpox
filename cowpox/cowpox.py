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

from . import APKPath, etc
from .android import AndroidProject, Assembly, AssetArchive, getbuildmode
from .arch import all_archs
from .bundle import PipInstallRecipe
from .config import Config
from .graph import Graph, GraphInfoImpl
from .make import Make
from .mirror import Mirror
from .platform import Platform, PlatformInfo
from .private import Private
from .util import Logging
from argparse import ArgumentParser
from aridimpl.model import Resolved, Text
from diapyr import DI
from lagoon import groupadd, python, useradd
from pathlib import Path
from pkg_resources import resource_filename
from tempfile import TemporaryDirectory
import grp, logging, os

log = logging.getLogger(__name__)

def _inituser(srcpath):
    uid, gid = (x for s in [srcpath.stat()] for x in [s.st_uid, s.st_gid])
    try:
        log.info("Group already exists: %s", grp.getgrgid(gid))
    except KeyError:
        groupadd.print('-g', gid, 'Cowpox')
    useradd.__create_home.print('-g', gid, '-u', uid, '--shell', '/bin/bash', 'Cowpox')
    os.setgid(gid)
    os.setuid(uid)
    del os.environ['HOME'] # XXX: Why is it set in the first place?

class EggInfoRequires(Resolved):

    @classmethod
    def factory(cls, context, pathresolvable):
        requires = Config(context.createchild(islist = True), [])
        requires.put('requires', resolvable = cls(pathresolvable.resolve(context).cat()))
        return requires._context

    def __init__(self, path):
        self.path = path

    def spread(self, _):
        with TemporaryDirectory() as tempdir:
            # FIXME: This will fail if there are any exotic imports.
            # FIXME: This invokes cythonize, but we should not write to mounted source.
            python.print('setup.py', 'egg_info', '-e', tempdir, cwd = self.path)
            egginfodir, = Path(tempdir).glob('*.egg-info')
            for r in (egginfodir / 'requires.txt').read_text().splitlines():
                yield r, Text(r)

def _main():
    logging = Logging()
    parser = ArgumentParser()
    parser.add_argument('config', nargs = '*')
    args = parser.parse_args()
    config = Config.blank()
    config.put('egg-info-requires', function = EggInfoRequires.factory)
    def applyargs():
        for text in args.config:
            config.exec(text)
    applyargs() # XXX: Use a prefix and fish out the src path only?
    config.load(resource_filename(etc.__name__, 'Cowpox.arid'))
    applyargs()
    _inituser(Path(config.container.src))
    logging.setpath(Path(config.log.path))
    with DI() as di:
        di.add(all_archs[config.android.arch])
        di.add(AndroidProject)
        di.add(Assembly)
        di.add(AssetArchive)
        di.add(config)
        di.add(di)
        di.add(getbuildmode)
        di.add(Graph)
        di.add(GraphInfoImpl)
        di.add(Make)
        di.add(Mirror)
        di.add(PipInstallRecipe)
        di.add(Platform)
        di.add(PlatformInfo)
        di.add(Private)
        for recipeimpl in di(GraphInfoImpl).recipeimpls.values():
            di.add(recipeimpl)
        return di(APKPath).relative_to(config.container.src)

def main_Cowpox():
    try:
        log.info("APK path: %s", _main())
    except:
        log.exception('Abort:')
        raise
