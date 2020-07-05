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
from .boot import Bootstrap
from .config import Config
from .context import GraphProxy, PipInstallRecipe
from .graph import GraphImpl, GraphInfoImpl
from .make import Make
from .mirror import Mirror
from .platform import Platform, PlatformInfo
from .private import PythonBundleImpl
from .util import findimpl, Logging
from argparse import ArgumentParser
from diapyr import DI
from lagoon import groupadd, python, useradd
from pathlib import Path
from pkg_resources import resource_filename
from tempfile import TemporaryDirectory
import logging, os

log = logging.getLogger(__name__)

def _inituser(srcpath):
    uid, gid = (x for s in [srcpath.stat()] for x in [s.st_uid, s.st_gid])
    groupadd.print('-g', gid, 'Cowpox')
    useradd.__create_home.print('-g', gid, '-u', uid, '--shell', '/bin/bash', 'Cowpox')
    os.setgid(gid)
    os.setuid(uid)
    del os.environ['HOME'] # XXX: Why is it set in the first place?

def _egginforequires(context, pathresolvable):
    # TODO LATER: This isn't lazy enough, which I suspect is the reason for multiple eval in high level API.
    requires = Config(context.createchild(islist = True), [])
    with TemporaryDirectory() as tempdir:
        python.print('setup.py', 'egg_info', '-e', tempdir, cwd = pathresolvable.resolve(context).cat())
        egginfodir, = Path(tempdir).glob('*.egg-info')
        for r in (egginfodir / 'requires.txt').read_text().splitlines():
            requires.put(r, text = r)
    return requires._context

def _main():
    logging = Logging()
    parser = ArgumentParser()
    parser.add_argument('srcpath', type = Path)
    args = parser.parse_args()
    _inituser(args.srcpath)
    config = Config.blank()
    config.put('container', 'src', text = str(args.srcpath))
    config.put('pyven', 'support', text = resource_filename(etc.__name__, 'pyven.arid'))
    config.put('egg-info-requires', function = _egginforequires)
    config.load(resource_filename(etc.__name__, 'root.arid'))
    config = config.Cowpox
    logging.setpath(Path(config.log.path))
    with DI() as di:
        di.add(all_archs[config.android.arch])
        di.add(findimpl(f"pythonforandroid.bootstraps.{config.bootstrap.name}", Bootstrap))
        di.add(AndroidProject)
        di.add(Assembly)
        di.add(AssetArchive)
        di.add(config)
        di.add(di)
        di.add(getbuildmode)
        di.add(GraphImpl)
        di.add(GraphInfoImpl)
        di.add(GraphProxy)
        di.add(Make)
        di.add(Mirror)
        di.add(PipInstallRecipe)
        di.add(Platform)
        di.add(PlatformInfo)
        di.add(PythonBundleImpl)
        for recipeimpl in di(GraphInfoImpl).recipeimpls():
            di.add(recipeimpl)
        return di(APKPath).relative_to(config.container.src)

def main_Cowpox():
    try:
        log.info("APK path: %s", _main())
    except:
        log.exception('Abort:')
        raise
