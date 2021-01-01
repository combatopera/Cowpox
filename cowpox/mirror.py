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

from aridity.config import Config
from diapyr import types
from hashlib import md5
from lagoon.util import atomic
from pathlib import Path
from urllib.request import Request, urlopen
import logging, time

log = logging.getLogger(__name__)

class Mirror:

    headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:83.0) Gecko/20100101 Firefox/83.0'}
    firstchunk = 1000000
    alpha = .1

    @types(Config)
    def __init__(self, config):
        self.mirror = Path(config.container.mirror)

    def download(self, url):
        mirrorpath = self.mirror / md5(url.encode('ascii')).hexdigest()
        if mirrorpath.exists():
            log.info("Already downloaded: %s", url)
        else:
            with urlopen(Request(url, headers = self.headers)) as f, atomic(mirrorpath) as partialpath, open(partialpath, 'wb') as g:
                total, chunksize = 0, self.firstchunk
                mark = time.time()
                while True:
                    data = f.read(chunksize)
                    if not data:
                        break
                    g.write(data)
                    total += len(data)
                    log.info("Total bytes: %s", total)
                    prev, mark = mark, time.time()
                    chunksize = round(chunksize / (mark - prev) * self.alpha + chunksize * (1 - self.alpha))
        return mirrorpath
