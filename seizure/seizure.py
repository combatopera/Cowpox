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
from .build import APKMaker
from .config import Config
from .context import Checks, ContextImpl
from .dirs import Dirs
from .mirror import Mirror
from .platform import Platform
from .src import Src
from .util import findimpl, Logging
from diapyr import DI, types
from p4a.recipe import Context
from p4a.boot import Bootstrap
from pathlib import Path
from pkg_resources import resource_filename
import logging

log = logging.getLogger(__name__)

class Result: pass

@types(Context, Dirs, Platform, TargetAndroid, Src, Checks, this = Result)
def run(context, dirs, platform, target, src, checks):
    platform.install()
    log.info('Compile platform')
    checks.check()
    context.build_recipes()
    src.copy_application_sources()
    dirs.add_sitecustomize()
    log.info('Package the application')
    return target.build_package()

def _main():
    logging = Logging()
    config = Config.load(resource_filename(etc.__name__, 'root.arid')).Seizure
    logging.setpath(Path(config.log.path))
    di = DI()
    try:
        di.add(config)
        di.add(all_archs[config.android.arch])
        di.add(findimpl(f"pythonforandroid.bootstraps.{config.p4a.bootstrap}", Bootstrap))
        di.add(di)
        di.add(APKMaker)
        di.add(Checks)
        di.add(ContextImpl)
        di.add(Dirs)
        di.add(Mirror)
        di.add(Platform)
        di.add(Src)
        di.add(TargetAndroid)
        di.add(run)
        return di(Result)
    finally:
        di.discardall()

def main():
    try:
        log.info("Result: %s", _main())
    except:
        log.exception('Abort:')
        raise
