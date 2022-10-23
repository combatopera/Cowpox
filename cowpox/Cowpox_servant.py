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

'Containerised component, not for direct invocation.'
from . import APKPath, Cowpox
from .android import AndroidProject, Assembly, AssetArchive, getbuildmode
from .arch import all_archs
from .bundle import PipInstallRecipe
from .graph import GraphImpl
from .make import Make
from .mirror import Mirror
from .platform import Platform, PlatformInfo
from .private import Private
from .util import coalesce, Logging
from argparse import ArgumentParser
from aridity.config import ConfigCtrl
from diapyr import DI
from lagoon import groupadd, useradd
from pathlib import Path
import grp, logging, os

log = logging.getLogger(__name__)

def _inituser(srcpath):
    uid, gid = (x for s in [srcpath.stat()] for x in [s.st_uid, s.st_gid])
    try:
        log.info("Group already exists: %s", grp.getgrgid(gid))
    except KeyError:
        groupadd[print]('-g', gid, 'Cowpox')
    useradd.__create_home[print]('-g', gid, '-u', uid, '--shell', '/bin/bash', 'Cowpox')
    os.setgid(gid)
    os.setuid(uid)
    del os.environ['HOME'] # XXX: Why is it set in the first place?

def _main():
    logging = Logging()
    root = ConfigCtrl()
    root.node.coalesce = coalesce
    root.load('/etc/settings.arid')
    config = root.loadappconfig(Cowpox.main, 'etc/Cowpox.arid')
    parser = ArgumentParser()
    parser.add_argument('--mirror')
    parser.add_argument('src')
    parser.parse_args(namespace = config.cli)
    srcpath = Path(config.container.src)
    (-config).load(srcpath / 'Cowpox.arid')
    _inituser(srcpath)
    logging.setpath(Path(config.log.path))
    with DI() as di:
        di.add(all_archs[config.android.arch])
        di.add(AndroidProject)
        di.add(Assembly)
        di.add(AssetArchive)
        di.add(config)
        di.add(di)
        di.add(getbuildmode)
        di.add(GraphImpl)
        di.add(Make)
        di.add(Mirror)
        di.add(PipInstallRecipe)
        di.add(Platform)
        di.add(PlatformInfo)
        di.add(Private)
        for builder in di(GraphImpl).builders:
            di.add(builder)
        return di(APKPath).relative_to(config.container.src)

def main():
    try:
        log.info("APK path: %s", _main())
    except:
        log.exception('Abort:')
        raise

if '__main__' == __name__:
    main()
