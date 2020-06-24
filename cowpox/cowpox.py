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

from . import etc
from .android import TargetAndroid
from .arch import all_archs
from .boot import Bootstrap
from .build import APKMaker
from .config import Config
from .context import ContextImpl, GraphImpl, GraphProxy, PipInstallRecipe
from .graph import GraphInfoImpl
from .make import Make
from .mirror import Mirror
from .platform import PlatformInfo
from .src import Src
from .util import findimpl, Logging
from argparse import ArgumentParser
from diapyr import DI, types
from lagoon import groupadd, useradd
from p4a import Context
from pathlib import Path
from pkg_resources import resource_filename
import logging, os

log = logging.getLogger(__name__)

class Result: pass

@types(Bootstrap, ContextImpl, Src, TargetAndroid, Make, this = Result)
def run(bootstrap, context, src, target, make):
    bootstrap.prepare_dirs()
    context.build_recipes()
    context.build_nonrecipes()
    make(bootstrap.dist_dir, bootstrap.run_distribute)
    make(src.app_dir, src.copy_application_sources)
    return target.build_package()

def _inituser(srcpath):
    uid, gid = (getattr(s, n) for s in [srcpath.stat()] for n in ['st_uid', 'st_gid'])
    groupadd.print('-g', gid, 'Cowpox')
    useradd.__create_home.print('-g', gid, '-u', uid, '--shell', '/bin/bash', 'Cowpox')
    os.setgid(gid)
    os.setuid(uid)

def _main():
    logging = Logging()
    parser = ArgumentParser()
    parser.add_argument('srcpath', type = Path)
    args = parser.parse_args()
    _inituser(args.srcpath)
    config = Config.blank()
    config.puttext('container', 'src', text = str(args.srcpath))
    config.load(resource_filename(etc.__name__, 'root.arid'))
    config = config.Cowpox
    logging.setpath(Path(config.log.path))
    with DI() as di:
        di.add(config)
        di.add(all_archs[config.android.arch])
        di.add(findimpl(f"pythonforandroid.bootstraps.{config.p4a.bootstrap}", Bootstrap))
        di.add(di)
        di.add(APKMaker)
        di.add(Context)
        di.add(ContextImpl)
        di.add(GraphImpl)
        di.add(GraphInfoImpl)
        di.add(GraphProxy)
        di.add(Make)
        di.add(Mirror)
        di.add(PipInstallRecipe)
        di.add(PlatformInfo)
        di.add(Src)
        di.add(TargetAndroid)
        di.add(run)
        di(GraphInfoImpl).configure(di)
        di(PlatformInfo).configure(di)
        return di(Result)

def main_Cowpox():
    try:
        log.info("Result: %s", _main())
    except:
        log.exception('Abort:')
        raise
