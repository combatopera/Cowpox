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

from jnius import PythonJavaClass, autoclass, java_method
from android.config import JAVA_NAMESPACE, JNI_NAMESPACE

_activity = autoclass(JAVA_NAMESPACE + '.PythonActivity').mActivity

_callbacks = {
    'on_new_intent': [],
    'on_activity_result': [],
}


class NewIntentListener(PythonJavaClass):
    __javainterfaces__ = [JNI_NAMESPACE + '/PythonActivity$NewIntentListener']
    __javacontext__ = 'app'

    def __init__(self, callback, **kwargs):
        super(NewIntentListener, self).__init__(**kwargs)
        self.callback = callback

    @java_method('(Landroid/content/Intent;)V')
    def onNewIntent(self, intent):
        self.callback(intent)


class ActivityResultListener(PythonJavaClass):
    __javainterfaces__ = [JNI_NAMESPACE + '/PythonActivity$ActivityResultListener']
    __javacontext__ = 'app'

    def __init__(self, callback):
        super(ActivityResultListener, self).__init__()
        self.callback = callback

    @java_method('(IILandroid/content/Intent;)V')
    def onActivityResult(self, requestCode, resultCode, intent):
        self.callback(requestCode, resultCode, intent)


def bind(**kwargs):
    for event, callback in kwargs.items():
        if event not in _callbacks:
            raise Exception('Unknown {!r} event'.format(event))
        elif event == 'on_new_intent':
            listener = NewIntentListener(callback)
            _activity.registerNewIntentListener(listener)
            _callbacks[event].append(listener)
        elif event == 'on_activity_result':
            listener = ActivityResultListener(callback)
            _activity.registerActivityResultListener(listener)
            _callbacks[event].append(listener)


def unbind(**kwargs):
    for event, callback in kwargs.items():
        if event not in _callbacks:
            raise Exception('Unknown {!r} event'.format(event))
        else:
            for listener in _callbacks[event][:]:
                if listener.callback == callback:
                    _callbacks[event].remove(listener)
                    if event == 'on_new_intent':
                        _activity.unregisterNewIntentListener(listener)
                    elif event == 'on_activity_result':
                        _activity.unregisterActivityResultListener(listener)
