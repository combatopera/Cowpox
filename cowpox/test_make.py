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

from .make import Make
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
import shutil

class TestMake(TestCase):

    maxDiff = None

    def setUp(self):
        self.logs = []
        self.tempdir = TemporaryDirectory()
        try:
            self.d = Path(self.tempdir.name)
            self.state = SimpleNamespace(path = self.d / 'yyup')
        except:
            self.tempdir.cleanup()
            raise

    def tearDown(self):
        self.tempdir.cleanup()

    def debug(self, *args):
        self.logs.append(['debug', *args])

    def info(self, *args):
        self.logs.append(['info', *args])

    def test_replay(self):
        m = Make(self, self)
        m(self.d / 'target1', lambda: self.logs.append('c1'))
        m(self.d / 'target2', lambda: self.logs.append('c2'))
        m = Make(self, self)
        m(self.d / 'target1', self.fail)
        m(self.d / 'target2', self.fail)
        m(self.d / 'target3', lambda: self.logs.append('c3'))
        self.assertEqual([
            ['info', "Create %s: %s", 'NOW', self.d / 'target1'], 'c1',
            ['info', "Create %s: %s", 'NOW', self.d / 'target2'], 'c2',
            ['info', "Create %s: %s", 'OK', self.d / 'target1'],
            ['info', "Create %s: %s", 'OK', self.d / 'target2'],
            ['info', "Create %s: %s", 'NOW', self.d / 'target3'], 'c3',
        ], self.logs)

    def test_update(self):
        m = Make(self, self)
        m(self.d / 'target1', lambda: self.logs.append('c1'))
        m(self.d / 'target2', lambda: self.logs.append('c2'))
        m(self.d / 'target1', lambda: self.logs.append('u11'))
        m(self.d / 'target2', lambda: self.logs.append('u21'))
        m(self.d / 'target2', lambda: self.logs.append('u22'))
        m = Make(self, self)
        m(self.d / 'target1', self.fail)
        m(self.d / 'target2', self.fail)
        m(self.d / 'target1', self.fail)
        m(self.d / 'target2', self.fail)
        m(self.d / 'target2', self.fail)
        m(self.d / 'target1', lambda: self.logs.append('u12'))
        self.assertEqual([
            ['info', "Create %s: %s", 'NOW', self.d / 'target1'], 'c1',
            ['info', "Create %s: %s", 'NOW', self.d / 'target2'], 'c2',
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target1'], 'u11',
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target2'], 'u21',
            ['info', "Update 2 %s: %s", 'NOW', self.d / 'target2'], 'u22',
            ['info', "Create %s: %s", 'OK', self.d / 'target1'],
            ['info', "Create %s: %s", 'OK', self.d / 'target2'],
            ['info', "Update 1 %s: %s", 'OK', self.d / 'target1'],
            ['info', "Update 1 %s: %s", 'OK', self.d / 'target2'],
            ['info', "Update 2 %s: %s", 'OK', self.d / 'target2'],
            ['info', "Update 2 %s: %s", 'NOW', self.d / 'target1'], 'u12',
        ], self.logs)

    def test_fork(self):
        m = Make(self, self)
        m(self.d / 'target1', lambda: self.logs.append('c1'))
        m(self.d / 'target2', lambda: self.logs.append('c2'))
        m(self.d / 'target1', lambda: self.logs.append('u11'))
        m(self.d / 'target2', lambda: self.logs.append('u21'))
        m(self.d / 'target3', lambda: self.logs.append('c3'))
        m = Make(self, self)
        m(self.d / 'target1', self.fail)
        m(self.d / 'target3', lambda: self.logs.append('c3'))
        m(self.d / 'target2', lambda: self.logs.append('c2'))
        m(self.d / 'target1', lambda: self.logs.append('u11'))
        m(self.d / 'target2', lambda: self.logs.append('u21'))
        m(self.d / 'target3', lambda: self.logs.append('u31'))
        self.assertEqual([
            ['info', "Create %s: %s", 'NOW', self.d / 'target1'], 'c1',
            ['info', "Create %s: %s", 'NOW', self.d / 'target2'], 'c2',
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target1'], 'u11',
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target2'], 'u21',
            ['info', "Create %s: %s", 'NOW', self.d / 'target3'], 'c3',
            ['info', "Create %s: %s", 'OK', self.d / 'target1'],
            ['info', "Create %s: %s", 'FRESH', self.d / 'target3'], 'c3',
            ['info', "Create %s: %s", 'NOW', self.d / 'target2'], 'c2',
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target1'], 'u11',
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target2'], 'u21',
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target3'], 'u31',
        ], self.logs)

    def test_config(self):
        m = Make(self, self)
        m(self.d / 'target1', lambda: self.logs.append('c1'))
        m('eranu')
        m(self.d / 'target2', lambda: self.logs.append('c2'))
        m = Make(self, self)
        m(self.d / 'target1', self.fail)
        m('eranu')
        m(self.d / 'target2', self.fail)
        m = Make(self, self)
        m(self.d / 'target1', self.fail)
        m('uvavu')
        m(self.d / 'target2', lambda: self.logs.append('c2'))
        self.assertEqual([
            ['info', "Create %s: %s", 'NOW', self.d / 'target1'], 'c1',
            ['info', "Config %s: %s", 'NOW', 'eranu'],
            ['info', "Create %s: %s", 'NOW', self.d / 'target2'], 'c2',
            ['info', "Create %s: %s", 'OK', self.d / 'target1'],
            ['info', "Config %s: %s", 'OK', 'eranu'],
            ['info', "Create %s: %s", 'OK', self.d / 'target2'],
            ['info', "Create %s: %s", 'OK', self.d / 'target1'],
            ['info', "Config %s: %s", 'FRESH', 'uvavu'],
            ['info', "Create %s: %s", 'NOW', self.d / 'target2'], 'c2',
        ], self.logs)

    def test_cleaned(self):
        m = Make(self, self)
        m(self.d / 'target1', lambda: self.logs.append('c1'))
        m(self.d / 'target2', lambda: self.logs.append('c2'))
        m(self.d / 'target1', lambda: self.logs.append('u11'))
        shutil.rmtree(self.d / 'target1')
        m = Make(self, self)
        m(self.d / 'target1', lambda: self.logs.append('c1'))
        m(self.d / 'target2', lambda: self.logs.append('c2'))
        m(self.d / 'target1', lambda: self.logs.append('u11'))
        self.assertEqual([
            ['info', "Create %s: %s", 'NOW', self.d / 'target1'], 'c1',
            ['info', "Create %s: %s", 'NOW', self.d / 'target2'], 'c2',
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target1'], 'u11',
            ['info', "Create %s: %s", 'AGAIN', self.d / 'target1'], 'c1',
            ['info', "Create %s: %s", 'NOW', self.d / 'target2'], 'c2',
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target1'], 'u11',
        ], self.logs)

    def test_cleaned2(self):
        m = Make(self, self)
        m(self.d / 'target1', lambda: self.logs.append('c1'))
        m(self.d / 'target2', lambda: self.logs.append('c2'))
        m(self.d / 'target1', lambda: self.logs.append('u11'))
        shutil.rmtree(self.d / 'target2')
        m = Make(self, self)
        m(self.d / 'target1', self.fail)
        m(self.d / 'target2', lambda: self.logs.append('c2'))
        m(self.d / 'target1', lambda: self.logs.append('u11'))
        self.assertEqual([
            ['info', "Create %s: %s", 'NOW', self.d / 'target1'], 'c1',
            ['info', "Create %s: %s", 'NOW', self.d / 'target2'], 'c2',
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target1'], 'u11',
            ['info', "Create %s: %s", 'OK', self.d / 'target1'],
            ['info', "Create %s: %s", 'AGAIN', self.d / 'target2'], 'c2',
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target1'], 'u11',
        ], self.logs)
