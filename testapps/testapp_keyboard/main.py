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

import os
print('imported os')
import sys
print('imported sys')

from kivy import platform

if platform == 'android':
    site_dir_path = './_python_bundle/site-packages'
    if not os.path.exists(site_dir_path):
        print('warning: site-packages dir not found: ' + site_dir_path)
    else:
        print('contents of ' + site_dir_path)
        print(os.listdir(site_dir_path))

    print('this dir is', os.path.abspath(os.curdir))

    print('contents of this dir', os.listdir('./'))

    if (os.path.exists(site_dir_path) and
            os.path.exists(site_dir_path + '/kivy/app.pyo')
            ):
        with open(site_dir_path + '/kivy/app.pyo', 'rb') as fileh:
            print('app.pyo size is', len(fileh.read()))

print('pythonpath is', sys.path)

import kivy
print('imported kivy')
print('file is', kivy.__file__)

from kivy.app import App

from kivy.lang import Builder
from kivy.properties import StringProperty

from kivy.uix.popup import Popup
from kivy.clock import Clock

print('Imported kivy')
from kivy.utils import platform
print('platform is', platform)


kv = '''
#:import Metrics kivy.metrics.Metrics
#:import Window kivy.core.window.Window

<FixedSizeButton@Button>:
    size_hint_y: None
    height: dp(60)


BoxLayout:
    orientation: 'vertical'
    BoxLayout:
        size_hint_y: None
        height: dp(50)
        orientation: 'horizontal'
        Button:
            text: 'None'
            on_press: Window.softinput_mode = ''
        Button:
            text: 'pan'
            on_press: Window.softinput_mode = 'pan'
        Button:
            text: 'below_target'
            on_press: Window.softinput_mode = 'below_target'
        Button:
            text: 'resize'
            on_press: Window.softinput_mode = 'resize'
    Widget:
        Scatter:
            id: scatter
            size_hint: None, None
            size: dp(300), dp(80)
            on_parent: self.pos = (300, 100)
            BoxLayout:
                size: scatter.size
                orientation: 'horizontal'
                canvas:
                    Color:
                        rgba: 1, 0, 0, 1
                    Rectangle:
                        pos: 0, 0
                        size: self.size
                Widget:
                    size_hint_x: None
                    width: dp(30)
                TextInput:
                    text: 'type in me'
'''


class ErrorPopup(Popup):
    error_text = StringProperty('')

def raise_error(error):
    print('ERROR:',  error)
    ErrorPopup(error_text=error).open()

class TestApp(App):
    def build(self):
        root = Builder.load_string(kv)
        Clock.schedule_interval(self.print_something, 2)
        # Clock.schedule_interval(self.test_pyjnius, 5)
        print('testing metrics')
        from kivy.metrics import Metrics
        print('dpi is', Metrics.dpi)
        print('density is', Metrics.density)
        print('fontscale is', Metrics.fontscale)
        return root

    def print_something(self, *args):
        print('App print tick', Clock.get_boottime())

    def on_pause(self):
        return True

    def test_pyjnius(self, *args):
        try:
            from jnius import autoclass, cast
        except ImportError:
            raise_error('Could not import pyjnius')
            return
        print('Attempting to vibrate with pyjnius')
        ANDROID_VERSION = autoclass('android.os.Build$VERSION')
        SDK_INT = ANDROID_VERSION.SDK_INT

        Context = autoclass("android.content.Context")
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity

        vibrator_service = activity.getSystemService(Context.VIBRATOR_SERVICE)
        vibrator = cast("android.os.Vibrator", vibrator_service)

        if vibrator and SDK_INT >= 26:
            print("Using android's `VibrationEffect` (SDK >= 26)")
            VibrationEffect = autoclass("android.os.VibrationEffect")
            vibrator.vibrate(
                VibrationEffect.createOneShot(
                    1000, VibrationEffect.DEFAULT_AMPLITUDE,
                ),
            )
        elif vibrator:
            print("Using deprecated android's vibrate (SDK < 26)")
            vibrator.vibrate(1000)
        else:
            print('Something happened...vibrator service disabled?')

    def test_ctypes(self, *args):
        import ctypes
            
    def test_numpy(self, *args):
        import numpy

        print(numpy.zeros(5))
        print(numpy.arange(5))
        print(numpy.random.random((3, 3)))

TestApp().run()
