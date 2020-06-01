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
from pkg_resources import resource_stream
import logging, shutil

log = logging.getLogger(__name__)

class Dirs:

    @types(Config)
    def __init__(self, config):
        workspace = Path(config.container.workspace)
        self.global_platform_dir = Path.home() / '.buildozer' / config.targetname / 'platform'
        self.buildozer_dir = workspace / '.buildozer'
        self.platform_dir = self.buildozer_dir / config.targetname / 'platform'
        self.app_dir = self.buildozer_dir / config.targetname / 'app'
        self.android_sdk_dir = self.global_platform_dir / 'android-sdk'
        self.android_ndk_dir = self.global_platform_dir / f"android-ndk-r{config.android.ndk}"

    def install(self):
        for path in self.global_platform_dir, self.platform_dir, self.app_dir:
            path.mkdirp()

    def add_sitecustomize(self):
        with resource_stream(__name__, 'sitecustomize.py') as f, (self.app_dir / 'sitecustomize.py').open('wb') as g:
            shutil.copyfileobj(f, g)
        main_py = self.app_dir / 'service' / 'main.py'
        if not main_py.exists():
            return
        with open(main_py, 'rb') as fd:
            data = fd.read()
        with open(main_py, 'wb') as fd:
            fd.write(b'import sys, os; sys.path = [os.path.join(os.getcwd(),"..", "_applibs")] + sys.path\n')
            fd.write(data)
        log.info('Patched service/main.py to include applibs')
