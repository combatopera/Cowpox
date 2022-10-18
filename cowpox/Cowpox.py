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

'Build APK for project.'
from pathlib import Path
from pkg_resources import iter_entry_points
import os, sys

host_mirror = Path.home() / '.cache' / 'Cowpox' / 'mirror'
container_mirror = '/mirror'
container_src = '/src'

def _tzoffset():
    from datetime import datetime, timedelta
    import time
    now = time.time()
    off = datetime.utcfromtimestamp(now) - datetime.fromtimestamp(now)
    return f"-{-off}" if off < timedelta() else f"+{off}"

def _imagetag():
    for ep in iter_entry_points('console_scripts'):
        if __name__ == ep.module_name:
            version = ep.dist.version
            return 'latest' if version.endswith('.dev0') else version

def main():
    host_mirror.mkdir(parents = True, exist_ok = True)
    command = [
        'docker', 'run', '--rm', '-i', *(['-t'] if sys.stdin.isatty() else []),
        '-v', f"{Path.cwd()}:{container_src}",
        '-v', f"{host_mirror}:{container_mirror}",
        '-e', f"TZ=COWPOX{_tzoffset()}",
        f"combatopera/cowpox:{_imagetag()}", # TODO LATER: Unduplicate with project.arid image name.
        '--mirror', container_mirror,
        container_src,
    ]
    os.execvp(command[0], command)

if '__main__' == __name__:
    main()
