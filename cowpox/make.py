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

from diapyr import types
from uuid import uuid4
import json, logging, shutil

log = logging.getLogger(__name__)

class Make:

    @types()
    def __init__(self, log = log):
        self.log = log

    def __call__(self, target, dependencies, install):
        infodir = target / '.Cowpox'
        infopath = infodir / 'info.json' # TODO: Exclude from artifact.
        okpath = infodir / 'OK'
        if okpath.exists():
            with infopath.open() as f:
                info = json.load(f)
            if info['dependencies'] == dependencies:
                self.log.info("[%s] Already OK.", target)
                return info['uuid']
            self.log.info("[%s] Rebuild due to changed dependencies.", target)
            shutil.rmtree(target)
        else:
            self.log.info("[%s] Start build.", target)
            if target.exists():
                self.log.warning("[%s] Delete.", target)
                shutil.rmtree(target)
            else:
                target.pmkdirp()
        install()
        uuid = str(uuid4())
        infodir.mkdir()
        with infopath.open('w') as f:
            json.dump(dict(dependencies = dependencies, uuid = uuid), f, indent = 4)
            print(file = f)
        okpath.mkdir()
        self.log.info("[%s] Build OK.", target)
        return uuid
