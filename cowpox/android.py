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

from .build import APKMaker
from .config import Config
from diapyr import types
from jproperties import Properties
from lagoon import gradle
from pathlib import Path
import logging, os, shutil

log = logging.getLogger(__name__)

class TargetAndroid:

    @types(Config, APKMaker)
    def __init__(self, config, apkmaker):
        self.arch = config.android.arch
        self.dist_name = config.package.name
        self.releasemode = 'debug' != config.build_mode
        self.p4a_whitelist = config.android.whitelist.list()
        self.version = config.version
        self.commit = config.commit
        self.apkdir = Path(config.apk.dir)
        self.dist_dir = Path(config.android.project.dir)
        self.gradleenv = dict(ANDROID_NDK_HOME = config.android_ndk_dir, ANDROID_HOME = config.android_sdk_dir)
        self.apkmaker = apkmaker

    @staticmethod
    def _check_p4a_sign_env(error):
        keys = ["KEYALIAS", "KEYSTORE_PASSWD", "KEYSTORE", "KEYALIAS_PASSWD"]
        check = True
        for key in keys:
            key = "P4A_RELEASE_{}".format(key)
            if key not in os.environ:
                if error:
                    log.error("Asking for release but %s is missing--sign will not be passed", key)
                check = False
        return check

    def _generate_whitelist(self):
        with (self.dist_dir / 'whitelist.txt').open('w') as f:
            for entry in self.p4a_whitelist:
                print(entry, file = f)

    def build_package(self):
        self._update_libraries_references()
        self._generate_whitelist()
        self.apkmaker.makeapkversion(self.releasemode and self._check_p4a_sign_env(True))
        gradle.__no_daemon.print('assembleRelease' if self.releasemode else 'assembleDebug', env = self.gradleenv, cwd = self.dist_dir)
        if not self.releasemode:
            mode_sign = mode = 'debug'
        else:
            mode_sign = 'release'
            mode = 'release' if self._check_p4a_sign_env(False) else 'release-unsigned'
        apkpath = self.apkdir / f"{self.dist_name}-{self.version}-{self.commit}-{self.arch}-{mode}.apk"
        shutil.copyfile(self.dist_dir / 'build' / 'outputs' / 'apk' / mode_sign / f"{self.dist_dir.name}-{mode}.apk", apkpath)
        log.info('Android packaging done!')
        return apkpath

    def _update_libraries_references(self):
        p = Properties()
        project_fn = self.dist_dir / 'project.properties'
        with project_fn.open('rb') as f:
            p.load(f)
        for key in [k for k in p if k.startswith('android.library.reference.')]:
            del p[key]
        with project_fn.open('wb') as f:
            p.store(f)
        log.debug('project.properties updated')
