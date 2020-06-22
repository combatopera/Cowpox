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
# Billing
cdef extern void android_billing_service_start()
cdef extern void android_billing_service_stop()
cdef extern void android_billing_buy(char *sku)
cdef extern char *android_billing_get_purchased_items()
cdef extern char *android_billing_get_pending_message()

class BillingService(object):

    BILLING_ACTION_SUPPORTED = 'billingsupported'
    BILLING_ACTION_ITEMSCHANGED = 'itemschanged'

    BILLING_TYPE_INAPP = 'inapp'
    BILLING_TYPE_SUBSCRIPTION = 'subs'

    def __init__(self, callback):
        super(BillingService, self).__init__()
        self.callback = callback
        self.purchased_items = None
        android_billing_service_start()

    def _stop(self):
        android_billing_service_stop()

    def buy(self, sku):
        cdef char *j_sku = <bytes>sku
        android_billing_buy(j_sku)

    def get_purchased_items(self):
        cdef char *items = NULL
        cdef bytes pitem
        items = android_billing_get_purchased_items()
        if items == NULL:
            return []
        pitems = items
        ret = {}
        for item in pitems.split('\n'):
            if not item:
                continue
            sku, qt = item.split(',')
            ret[sku] = {'qt': int(qt)}
        return ret

    def check(self, *largs):
        cdef char *message
        cdef bytes pymessage

        while True:
            message = android_billing_get_pending_message()
            if message == NULL:
                break
            pymessage = <bytes>message
            self._handle_message(pymessage)

        if self.purchased_items is None:
            self._check_new_items()

    def _handle_message(self, message):
        action, data = message.split('|', 1)
        #print "HANDLE MESSAGE-----", (action, data)

        if action == 'billingSupported':
            tp, value = data.split('|')
            value = True if value == '1' else False
            self.callback(BillingService.BILLING_ACTION_SUPPORTED, tp, value)

        elif action == 'requestPurchaseResponse':
            self._check_new_items()

        elif action == 'purchaseStateChange':
            self._check_new_items()

        elif action == 'restoreTransaction':
            self._check_new_items()

    def _check_new_items(self):
        items = self.get_purchased_items()
        if self.purchased_items != items:
            self.purchased_items = items
            self.callback(BillingService.BILLING_ACTION_ITEMSCHANGED, self.purchased_items)
