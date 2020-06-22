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


# This test is a special case that we expect to run under Python 2, so
# include the necessary compatibility imports:
try:  # Python 3
    from unittest import mock
except ImportError:  # Python 2
    import mock

from pythonforandroid.recommendations import PY2_ERROR_TEXT
from pythonforandroid import entrypoints


def test_main_python2():
    """Test that running under Python 2 leads to the build failing, while
    running under a suitable version works fine.

    Note that this test must be run *using* Python 2 to truly test
    that p4a can reach the Python version check before importing some
    Python-3-only syntax and crashing.
    """

    # Under Python 2, we should get a normal control flow exception
    # that is handled properly, not any other type of crash
    handle_exception_path = 'pythonforandroid.entrypoints.handle_build_exception'
    with mock.patch('sys.version_info') as fake_version_info, \
         mock.patch(handle_exception_path) as handle_build_exception:  # noqa: E127

        fake_version_info.major = 2
        fake_version_info.minor = 7

        def check_python2_exception(exc):
            """Check that the exception message is Python 2 specific."""
            assert exc.message == PY2_ERROR_TEXT
        handle_build_exception.side_effect = check_python2_exception

        entrypoints.main()

    handle_build_exception.assert_called_once()
