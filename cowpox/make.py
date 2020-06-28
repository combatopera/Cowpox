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
from diapyr import types
from pathlib import Path
import logging, shutil

log = logging.getLogger(__name__)

class BulkOK: pass

class Make:

    cursor = 0

    @types(Config)
    def __init__(self, config, log = log):
        self.statepath = Path(config.state.path)
        if self.statepath.exists():
            with self.statepath.open() as f:
                self.targetstrs = f.read().splitlines()
        else:
            self.targetstrs = []
        self.log = log

    def __call__(self, target, install = None):
        targetstr = str(target)
        if install is None:
            format = "Config %s: %s"
        else:
            n = self.targetstrs[:self.cursor].count(targetstr)
            format = f"Update {n} %s: %s" if n else "Create %s: %s"
        if self.cursor < len(self.targetstrs):
            if self.targetstrs[self.cursor] == targetstr:
                if install is None or target.exists():
                    self.log.info(format, 'OK', target)
                    self.cursor += 1
                    return
                when = 'AGAIN'
            else:
                when = 'FRESH'
            del self.targetstrs[self.cursor:]
        else:
            when = 'NOW'
        self.log.info(format, when, target)
        if install is not None:
            if not n:
                if target.exists():
                    self.log.warning("Delete: %s", target)
                    shutil.rmtree(target)
                else:
                    target.parent.mkdir(parents = True, exist_ok = True)
            install()
        self.targetstrs.append(targetstr)
        with self.statepath.open('w') as f:
            for t in self.targetstrs:
                print(t, file = f)
        self.cursor += 1
