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

'''
Clone Python implementation of Kivy Launcher from kivy/kivy-launcher repo,
install deps specified in the OPTIONS['apk']['requirements'] and put it
to a dist named OPTIONS['apk']['dist-name'].

Tested with P4A Dockerfile at 5fc5241e01fbbc2b23b3749f53ab48f22239f4fc,
kivy-launcher at ad5c5c6e886a310bf6dd187e992df972864d1148 on Windows 8.1
with Docker for Windows and running on Samsung Galaxy Note 9, Android 8.1.

docker run \
    --interactive \
    --tty \
    -v "/c/Users/.../python-for-android/testapps":/home/user/testapps \
    -v ".../python-for-android/pythonforandroid":/home/user/pythonforandroid \
    p4a sh -c '\
        . venv/bin/activate \
        && cd testapps/testlauncherreboot_setup \
        && python sdl2.py apk \
            --sdk-dir $ANDROID_SDK_HOME \
            --ndk-dir $ANDROID_NDK_HOME'
'''

# pylint: disable=import-error,no-name-in-module
from subprocess import Popen
from distutils.core import setup
from os import listdir
from os.path import join, dirname, abspath, exists
from pprint import pprint
from setuptools import find_packages

ROOT = dirname(abspath(__file__))
LAUNCHER = join(ROOT, 'launcherapp')

if not exists(LAUNCHER):
    PROC = Popen([
        'git', 'clone',
        'https://github.com/kivy/kivy-launcher',
        LAUNCHER
    ])
    PROC.communicate()
    assert PROC.returncode == 0, PROC.returncode

    pprint(listdir(LAUNCHER))
    pprint(listdir(ROOT))


OPTIONS = {
    'apk': {
        'debug': None,
        'bootstrap': 'sdl2',
        'requirements': (
            'python3,sdl2,kivy,android,pyjnius,plyer'
        ),
        # 'sqlite3,docutils,pygments,'
        # 'cymunk,lxml,pil,openssl,pyopenssl,'
        # 'twisted,audiostream,ffmpeg,numpy'

        'android-api': 27,
        'ndk-api': 21,
        'dist-name': 'bdisttest_python3launcher_sdl2_googlendk',
        'name': 'TestLauncherPy3-sdl2',
        'package': 'org.kivy.testlauncherpy3_sdl2_googlendk',
        'ndk-version': '10.3.2',
        'arch': 'armeabi-v7a',
        'permissions': [
            'ACCESS_COARSE_LOCATION', 'ACCESS_FINE_LOCATION',
            'BLUETOOTH', 'BODY_SENSORS', 'CAMERA', 'INTERNET',
            'NFC', 'READ_EXTERNAL_STORAGE', 'RECORD_AUDIO',
            'USE_FINGERPRINT', 'VIBRATE', 'WAKE_LOCK',
            'WRITE_EXTERNAL_STORAGE'
        ]
    }
}

PACKAGE_DATA = {
    'launcherapp': [
        '*.py', '*.png', '*.ttf', '*.eot', '*.svg', '*.woff',
    ],
    'launcherapp/art': [
        '*.py', '*.png', '*.ttf', '*.eot', '*.svg', '*.woff',
    ],
    'launcherapp/art/fontello': [
        '*.py', '*.png', '*.ttf', '*.eot', '*.svg', '*.woff',
    ],
    'launcherapp/data': [
        '*.py', '*.png', '*.ttf', '*.eot', '*.svg', '*.woff',
    ],
    'launcherapp/launcher': [
        '*.py', '*.png', '*.ttf', '*.eot', '*.svg', '*.woff',
    ]
}

PACKAGES = find_packages()
print('packages are', PACKAGES)

setup(
    name='testlauncherpy3_sdl2_googlendk',
    version='1.0',
    description='p4a sdl2.py apk',
    author='Peter Badida',
    author_email='keyweeusr@gmail.com',
    packages=find_packages(),
    options=OPTIONS,
    package_data=PACKAGE_DATA
)
