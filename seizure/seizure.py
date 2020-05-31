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

from .android import TargetAndroid
from .config import Config
from .jsonstore import JsonStore
from .dirs import Dirs
from .src import Src
from argparse import ArgumentParser
from chromalog.log import ColorizingFormatter, ColorizingStreamHandler
from diapyr import DI, types
from lagoon import pipify, soak
from pathlib import Path
import logging, os, shutil

log = logging.getLogger(__name__)

class Result: pass

@types(Dirs, TargetAndroid, Src, this = Result)
def run(dirs, target, src):
    dirs.install()
    log.info('Install platform')
    target.install_platform() # TODO: Bake these into the image.
    log.info('Compile platform')
    target.compile_platform()
    src._copy_application_sources()
    shutil.copytree(dirs.applibs_dir, dirs.app_dir / '_applibs')
    dirs.add_sitecustomize()
    log.info('Package the application')
    target.build_package()

def _initlogging():
    console = ColorizingStreamHandler()
    console.setLevel(logging.INFO)
    formatter = ColorizingFormatter("%(asctime)s [%(levelname)s] %(message)s")
    for h in logging.FileHandler('/workspace/bin/Seizure.log'), console:
        h.setFormatter(formatter)
        logging.root.addHandler(h)
    logging.root.setLevel(logging.DEBUG)

def _main():
    _initlogging()
    parser = ArgumentParser()
    parser.add_argument('configpath')
    config = Config.load(parser.parse_args().configpath).Seizure
    shutil.copytree('.', config.container.project, symlinks = True, dirs_exist_ok = True)
    workspace = Path(config.container.workspace)
    soak.print(cwd = workspace)
    pipify.print('-f', workspace / 'bdozlib.arid', cwd = config.container.project)
    # TODO: Run in arbitrary directory.
    os.chdir(workspace) # FIXME LATER: Only include main.py in artifact.
    di = DI()
    try:
        di.add(config)
        di.add(Dirs)
        di.add(JsonStore) # TODO: Retire.
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
