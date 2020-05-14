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

from .logger import info, warning
from .util import urlretrieve
from diapyr.util import singleton
from hashlib import md5
from pathlib import Path
import logging, os, sys, time

log = logging.getLogger(__name__)

@singleton
class Mirror:

    mirror = Path('/mirror') # TODO: Make configurable.

    @staticmethod
    def report_hook(index, blksize, size):
        if size <= 0:
            progression = '{0} bytes'.format(index * blksize)
        else:
            progression = '{0:.2f}%'.format(index * blksize * 100. / float(size))
        if "CI" not in os.environ:
            sys.stdout.write('- Download {}\r'.format(progression))
            sys.stdout.flush()

    def download(self, url):
        mirrorpath = self.mirror / md5(url.encode('ascii')).hexdigest()
        if mirrorpath.exists():
            info("Already downloaded: %s", url) # XXX: How to enable debug?
        else:
            partialpath = mirrorpath.with_name(mirrorpath.name + '.part')
            attempts = 0
            while True:
                try:
                    urlretrieve(url, partialpath, self.report_hook)
                    break
                except OSError:
                    attempts += 1
                    if attempts >= 5:
                        raise
                warning('Download failed retrying in a second...')
                time.sleep(1)
            partialpath.rename(mirrorpath)
        return mirrorpath

def download(url, filename, cwd):
    url = url + filename
    filename = Path(cwd, filename)
    if filename.exists():
        filename.unlink()
    log.debug('Downloading %s', url)
    Path(filename).symlink_to(Mirror.download(url))
    return filename
