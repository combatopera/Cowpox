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

from pythonforandroid.toolchain import Recipe

# if android app crashes on start with "ImportError: No module named websocket"
#
#     copy the 'websocket' directory into your app directory to force inclusion.
#
# see my example at https://github.com/debauchery1st/example_kivy_websocket-recipe
#
# If you see errors relating to 'SSL not available' ensure you have the package backports.ssl-match-hostname
# in the buildozer requirements, since Kivy targets python 2.7.x
#
# You may also need sslopt={"cert_reqs": ssl.CERT_NONE} as a parameter to ws.run_forever() if you get an error relating to
# host verification


class WebSocketClient(Recipe):

    url = 'https://github.com/websocket-client/websocket-client/archive/v{version}.tar.gz'

    version = '0.40.0'

    # patches = ['websocket.patch']  # Paths relative to the recipe dir

    depends = ['android', 'pyjnius', 'cryptography', 'pyasn1', 'pyopenssl']


recipe = WebSocketClient()
