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
    events = 0

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

    def info(self, *args):
        self.logs.append(['info', *args])

    def warning(self, *args):
        self.logs.append(['warn', *args])

    def _mkdir(self, relpath):
        def install():
            (self.d / relpath).mkdir()
            self._update()
        return install

    def _update(self):
        self.events += 1
        self.logs.append(self.events)

    def test_replay(self):
        m = Make(self, self)
        m(self.d / 'target1', self._mkdir('target1'))
        m(self.d / 'target2', self._mkdir('target2'))
        self.assertEqual(list(map(str, [
            self.d / 'target1',
            self.d / 'target2',
        ])), m.targetstrs)
        m = Make(self, self)
        m(self.d / 'target1', self.fail)
        m(self.d / 'target2', self.fail)
        m(self.d / 'target3', self._mkdir('target3'))
        self.assertEqual(list(map(str, [
            self.d / 'target1',
            self.d / 'target2',
            self.d / 'target3',
        ])), m.targetstrs)
        self.assertEqual([
            ['info', "Create %s: %s", 'NOW', self.d / 'target1'], 1,
            ['info', "Create %s: %s", 'NOW', self.d / 'target2'], 2,
            ['info', "Create %s: %s", 'OK', self.d / 'target1'],
            ['info', "Create %s: %s", 'OK', self.d / 'target2'],
            ['info', "Create %s: %s", 'NOW', self.d / 'target3'], 3,
        ], self.logs)

    def test_update(self):
        m = Make(self, self)
        m(self.d / 'target1', self._mkdir('target1'))
        m(self.d / 'target2', self._mkdir('target2'))
        m(self.d / 'target1', self._update)
        m(self.d / 'target2', self._update)
        m(self.d / 'target2', self._update)
        self.assertEqual(list(map(str, [
            self.d / 'target1',
            self.d / 'target2',
            self.d / 'target1',
            self.d / 'target2',
            self.d / 'target2',
        ])), m.targetstrs)
        m = Make(self, self)
        m(self.d / 'target1', self.fail)
        m(self.d / 'target2', self.fail)
        m(self.d / 'target1', self.fail)
        m(self.d / 'target2', self.fail)
        m(self.d / 'target2', self.fail)
        m(self.d / 'target1', self._update)
        self.assertEqual(list(map(str, [
            self.d / 'target1',
            self.d / 'target2',
            self.d / 'target1',
            self.d / 'target2',
            self.d / 'target2',
            self.d / 'target1',
        ])), m.targetstrs)
        self.assertEqual([
            ['info', "Create %s: %s", 'NOW', self.d / 'target1'], 1,
            ['info', "Create %s: %s", 'NOW', self.d / 'target2'], 2,
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target1'], 3,
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target2'], 4,
            ['info', "Update 2 %s: %s", 'NOW', self.d / 'target2'], 5,
            ['info', "Create %s: %s", 'OK', self.d / 'target1'],
            ['info', "Create %s: %s", 'OK', self.d / 'target2'],
            ['info', "Update 1 %s: %s", 'OK', self.d / 'target1'],
            ['info', "Update 1 %s: %s", 'OK', self.d / 'target2'],
            ['info', "Update 2 %s: %s", 'OK', self.d / 'target2'],
            ['info', "Update 2 %s: %s", 'NOW', self.d / 'target1'], 6,
        ], self.logs)

    def test_fork(self):
        m = Make(self, self)
        m(self.d / 'target1', self._mkdir('target1'))
        m(self.d / 'target2', self._mkdir('target2'))
        m(self.d / 'target1', self._update)
        m(self.d / 'target2', self._update)
        m(self.d / 'target3', self._mkdir('target3'))
        self.assertEqual(list(map(str, [
            self.d / 'target1',
            self.d / 'target2',
            self.d / 'target1',
            self.d / 'target2',
            self.d / 'target3',
        ])), m.targetstrs)
        m = Make(self, self)
        m(self.d / 'target1', self.fail)
        m(self.d / 'target3', self._mkdir('target3'))
        m(self.d / 'target2', self._mkdir('target2'))
        m(self.d / 'target1', self._update)
        m(self.d / 'target2', self._update)
        m(self.d / 'target3', self._update)
        self.assertEqual(list(map(str, [
            self.d / 'target1',
            self.d / 'target3',
            self.d / 'target2',
            self.d / 'target1',
            self.d / 'target2',
            self.d / 'target3',
        ])), m.targetstrs)
        self.assertEqual([
            ['info', "Create %s: %s", 'NOW', self.d / 'target1'], 1,
            ['info', "Create %s: %s", 'NOW', self.d / 'target2'], 2,
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target1'], 3,
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target2'], 4,
            ['info', "Create %s: %s", 'NOW', self.d / 'target3'], 5,
            ['info', "Create %s: %s", 'OK', self.d / 'target1'],
            ['info', "Create %s: %s", 'FRESH', self.d / 'target3'], ['warn', "Delete: %s", self.d / 'target3'], 6,
            ['info', "Create %s: %s", 'NOW', self.d / 'target2'], ['warn', "Delete: %s", self.d / 'target2'], 7,
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target1'], 8,
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target2'], 9,
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target3'], 10,
        ], self.logs)

    def test_config(self):
        m = Make(self, self)
        m(self.d / 'target1', self._mkdir('target1'))
        m('eranu')
        m(self.d / 'target2', self._mkdir('target2'))
        self.assertEqual(list(map(str, [
            self.d / 'target1',
            'eranu',
            self.d / 'target2',
        ])), m.targetstrs)
        m = Make(self, self)
        m(self.d / 'target1', self.fail)
        m('eranu')
        m(self.d / 'target2', self.fail)
        self.assertEqual(list(map(str, [
            self.d / 'target1',
            'eranu',
            self.d / 'target2',
        ])), m.targetstrs)
        m = Make(self, self)
        m(self.d / 'target1', self.fail)
        m('uvavu')
        m(self.d / 'target2', self._mkdir('target2'))
        self.assertEqual(list(map(str, [
            self.d / 'target1',
            'uvavu',
            self.d / 'target2',
        ])), m.targetstrs)
        self.assertEqual([
            ['info', "Create %s: %s", 'NOW', self.d / 'target1'], 1,
            ['info', "Config %s: %s", 'NOW', 'eranu'],
            ['info', "Create %s: %s", 'NOW', self.d / 'target2'], 2,
            ['info', "Create %s: %s", 'OK', self.d / 'target1'],
            ['info', "Config %s: %s", 'OK', 'eranu'],
            ['info', "Create %s: %s", 'OK', self.d / 'target2'],
            ['info', "Create %s: %s", 'OK', self.d / 'target1'],
            ['info', "Config %s: %s", 'FRESH', 'uvavu'],
            ['info', "Create %s: %s", 'NOW', self.d / 'target2'], ['warn', "Delete: %s", self.d / 'target2'], 3,
        ], self.logs)

    def test_cleaned(self):
        m = Make(self, self)
        m(self.d / 'target1', self._mkdir('target1'))
        m(self.d / 'target2', self._mkdir('target2'))
        m(self.d / 'target1', self._update)
        self.assertEqual(list(map(str, [
            self.d / 'target1',
            self.d / 'target2',
            self.d / 'target1',
        ])), m.targetstrs)
        shutil.rmtree(self.d / 'target1')
        m = Make(self, self)
        m(self.d / 'target1', self._mkdir('target1'))
        m(self.d / 'target2', self._mkdir('target2'))
        m(self.d / 'target1', self._update)
        self.assertEqual(list(map(str, [
            self.d / 'target1',
            self.d / 'target2',
            self.d / 'target1',
        ])), m.targetstrs)
        self.assertEqual([
            ['info', "Create %s: %s", 'NOW', self.d / 'target1'], 1,
            ['info', "Create %s: %s", 'NOW', self.d / 'target2'], 2,
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target1'], 3,
            ['info', "Create %s: %s", 'AGAIN', self.d / 'target1'], 4,
            ['info', "Create %s: %s", 'NOW', self.d / 'target2'], ['warn', "Delete: %s", self.d / 'target2'], 5,
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target1'], 6,
        ], self.logs)

    def test_cleaned2(self):
        m = Make(self, self)
        m(self.d / 'target1', self._mkdir('target1'))
        m(self.d / 'target2', self._mkdir('target2'))
        m(self.d / 'target1', self._update)
        self.assertEqual(list(map(str, [
            self.d / 'target1',
            self.d / 'target2',
            self.d / 'target1',
        ])), m.targetstrs)
        shutil.rmtree(self.d / 'target2')
        m = Make(self, self)
        m(self.d / 'target1', self.fail)
        m(self.d / 'target2', self._mkdir('target2'))
        m(self.d / 'target1', self._update)
        self.assertEqual(list(map(str, [
            self.d / 'target1',
            self.d / 'target2',
            self.d / 'target1',
        ])), m.targetstrs)
        self.assertEqual([
            ['info', "Create %s: %s", 'NOW', self.d / 'target1'], 1,
            ['info', "Create %s: %s", 'NOW', self.d / 'target2'], 2,
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target1'], 3,
            ['info', "Create %s: %s", 'OK', self.d / 'target1'],
            ['info', "Create %s: %s", 'AGAIN', self.d / 'target2'], 4,
            ['info', "Update 1 %s: %s", 'NOW', self.d / 'target1'], 5,
        ], self.logs)
