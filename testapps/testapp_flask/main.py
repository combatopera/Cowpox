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

print('main.py was successfully called')
print('this is the new main.py')

import sys
print('python version is: ' + sys.version)
print('python path is', sys.path)

import os
print('imported os')

import flask
print('flask1???')

print('contents of this dir', os.listdir('./'))

import flask
print('flask???')


from flask import Flask
app = Flask(__name__)

from flask import (Flask, url_for, render_template, request, redirect,
                   flash)

print('imported flask etc')
print('importing pyjnius')

from jnius import autoclass, cast

ANDROID_VERSION = autoclass('android.os.Build$VERSION')
SDK_INT = ANDROID_VERSION.SDK_INT
Context = autoclass('android.content.Context')
PythonActivity = autoclass('org.kivy.android.PythonActivity')
activity = PythonActivity.mActivity

vibrator_service = activity.getSystemService(Context.VIBRATOR_SERVICE)
vibrator = cast("android.os.Vibrator", vibrator_service)

ActivityInfo = autoclass('android.content.pm.ActivityInfo')

@app.route('/')
def page1():
    return render_template('index.html')

@app.route('/page2')
def page2():
    return render_template('page2.html')

@app.route('/vibrate')
def vibrate():
    args = request.args
    if 'time' not in args:
        print('ERROR: asked to vibrate but without time argument')
    print('asked to vibrate', args['time'])

    if vibrator and SDK_INT >= 26:
        print("Using android's `VibrationEffect` (SDK >= 26)")
        VibrationEffect = autoclass("android.os.VibrationEffect")
        vibrator.vibrate(
            VibrationEffect.createOneShot(
                int(float(args['time']) * 1000),
                VibrationEffect.DEFAULT_AMPLITUDE,
            ),
        )
    elif vibrator:
        print("Using deprecated android's vibrate (SDK < 26)")
        vibrator.vibrate(int(float(args['time']) * 1000))
    else:
        print('Something happened...vibrator service disabled?')
    print('vibrated')

@app.route('/loadUrl')
def loadUrl():
    args = request.args
    if 'url' not in args:
        print('ERROR: asked to open an url but without url argument')
    print('asked to open url', args['url'])
    activity.loadUrl(args['url'])

@app.route('/orientation')
def orientation():
    args = request.args
    if 'dir' not in args:
        print('ERROR: asked to orient but no dir specified')
    direction = args['dir']
    if direction not in ('horizontal', 'vertical'):
        print('ERROR: asked to orient to neither horizontal nor vertical')

    if direction == 'horizontal':
        activity.setRequestedOrientation(
            ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE)
    else:
        activity.setRequestedOrientation(
            ActivityInfo.SCREEN_ORIENTATION_PORTRAIT)


from os import curdir
from os.path import realpath
print('curdir', realpath(curdir))
if realpath(curdir).startswith('/data'):
    app.run(debug=False)
else:
    app.run(debug=True)
