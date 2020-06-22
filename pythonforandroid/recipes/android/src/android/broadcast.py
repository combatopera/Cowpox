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

# -------------------------------------------------------------------
# Broadcast receiver bridge

from jnius import autoclass, PythonJavaClass, java_method
from android.config import JAVA_NAMESPACE, JNI_NAMESPACE


class BroadcastReceiver(object):

    class Callback(PythonJavaClass):
        __javainterfaces__ = [JNI_NAMESPACE + '/GenericBroadcastReceiverCallback']
        __javacontext__ = 'app'

        def __init__(self, callback, *args, **kwargs):
            self.callback = callback
            PythonJavaClass.__init__(self, *args, **kwargs)

        @java_method('(Landroid/content/Context;Landroid/content/Intent;)V')
        def onReceive(self, context, intent):
            self.callback(context, intent)

    def __init__(self, callback, actions=None, categories=None):
        super(BroadcastReceiver, self).__init__()
        self.callback = callback

        if not actions and not categories:
            raise Exception('You need to define at least actions or categories')

        def _expand_partial_name(partial_name):
            if '.' in partial_name:
                return partial_name  # Its actually a full dotted name
            else:
                name = 'ACTION_{}'.format(partial_name.upper())
                if not hasattr(Intent, name):
                    raise Exception('The intent {} doesnt exist'.format(name))
                return getattr(Intent, name)

        # resolve actions/categories first
        Intent = autoclass('android.content.Intent')
        resolved_actions = [_expand_partial_name(x) for x in actions or []]
        resolved_categories = [_expand_partial_name(x) for x in categories or []]

        # resolve android API
        GenericBroadcastReceiver = autoclass(JAVA_NAMESPACE + '.GenericBroadcastReceiver')
        IntentFilter = autoclass('android.content.IntentFilter')
        HandlerThread = autoclass('android.os.HandlerThread')

        # create a thread for handling events from the receiver
        self.handlerthread = HandlerThread('handlerthread')

        # create a listener
        self.listener = BroadcastReceiver.Callback(self.callback)
        self.receiver = GenericBroadcastReceiver(self.listener)
        self.receiver_filter = IntentFilter()
        for x in resolved_actions:
            self.receiver_filter.addAction(x)
        for x in resolved_categories:
            self.receiver_filter.addCategory(x)

    def start(self):
        Handler = autoclass('android.os.Handler')
        self.handlerthread.start()
        self.handler = Handler(self.handlerthread.getLooper())
        self.context.registerReceiver(
            self.receiver, self.receiver_filter, None, self.handler)

    def stop(self):
        self.context.unregisterReceiver(self.receiver)
        self.handlerthread.quit()

    @property
    def context(self):
        from os import environ
        if 'PYTHON_SERVICE_ARGUMENT' in environ:
            PythonService = autoclass(JAVA_NAMESPACE + '.PythonService')
            return PythonService.mService
        PythonActivity = autoclass(JAVA_NAMESPACE + '.PythonActivity')
        return PythonActivity.mActivity
