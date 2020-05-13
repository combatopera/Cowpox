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

from .config import Config
from lagoon import pipify, soak
from pathlib import Path
import logging, os, shutil

log = logging.getLogger(__name__)

def disablegradledaemon():
    path = Path.home() / '.gradle' / 'gradle.properties'
    line = 'org.gradle.daemon=false'
    try:
        with path.open() as f:
            if line == f.read().splitlines()[-1]:
                log.debug('Gradle Daemon already disabled.')
                return
    except FileNotFoundError:
        pass
    log.info('Disabling Gradle Daemon.')
    with path.open('a') as f:
        print(line, file = f)

def main():
    logging.basicConfig(format = "[%(levelname)s] %(message)s", level = logging.DEBUG)
    disablegradledaemon()
    shutil.copytree('.', '/project', symlinks = True, dirs_exist_ok = True)
    soak.print(cwd = '/workspace')
    pipify.print('-f', '/workspace/bdozlib.arid', cwd = '/project')
    os.chdir('/workspace') # FIXME: Only include main.py in artifact.
    from .buildozer import Buildozer # FIXME: Do not resolve paths so eagerly.
    Buildozer(Config()).android_debug()
