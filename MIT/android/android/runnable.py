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
Runnable
========

'''

from jnius import PythonJavaClass, java_method, autoclass
from android.config import JAVA_NAMESPACE

# reference to the activity
_PythonActivity = autoclass(JAVA_NAMESPACE + '.PythonActivity')


class Runnable(PythonJavaClass):
    '''Wrapper around Java Runnable class. This class can be used to schedule a
    call of a Python function into the PythonActivity thread.
    '''

    __javainterfaces__ = ['java/lang/Runnable']
    __runnables__ = []

    def __init__(self, func):
        super(Runnable, self).__init__()
        self.func = func

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        Runnable.__runnables__.append(self)
        _PythonActivity.mActivity.runOnUiThread(self)

    @java_method('()V')
    def run(self):
        try:
            self.func(*self.args, **self.kwargs)
        except:  # noqa E722
            import traceback
            traceback.print_exc()

        Runnable.__runnables__.remove(self)


def run_on_ui_thread(f):
    '''Decorator to create automatically a :class:`Runnable` object with the
    function. The function will be delayed and call into the Activity thread.
    '''
    def f2(*args, **kwargs):
        Runnable(f)(*args, **kwargs)
    return f2
