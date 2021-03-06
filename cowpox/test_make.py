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
from unittest import TestCase
import shutil

class I: pass

class W: pass

class TestMake(TestCase):

    def setUp(self):
        self.logs = []
        self.make = Make(self)

    def info(self, *args):
        self.logs.extend([I, *args])

    def warning(self, *args):
        self.logs.extend([W, *args])

    def _pop(self):
        v = self.logs.copy()
        self.logs.clear()
        return v

    def _make(self):
        self.uuid = self.make(self.target, self.dependencies, self.install)
        return self.uuid

    def test_works(self):
        with TemporaryDirectory() as tempdir:
            self.target = target = Path(tempdir, 'a')
            self.dependencies = None
            self.install = target.mkdir
            self._make()
            self.assertEqual([
                I, "[%s] Start build.", target,
                I, "[%s] Build OK.", target,
            ], self._pop())
            self.assertEqual(self.uuid, self._make())
            self.assertEqual([
                I, "[%s] Already OK.", target,
            ], self._pop())
            (target / '.Cowpox' / 'OK').rmdir()
            self.assertNotEqual(self.uuid, self._make())
            self.assertEqual([
                I, "[%s] Start build.", target,
                W, "[%s] Delete.", target,
                I, "[%s] Build OK.", target,
            ], self._pop())
            shutil.rmtree(target)
            self.assertNotEqual(self.uuid, self._make())
            self.assertEqual([
                I, "[%s] Start build.", target,
                I, "[%s] Build OK.", target,
            ], self._pop())

    def test_dependencies(self):
        with TemporaryDirectory() as tempdir:
            self.target = target = Path(tempdir, 'a')
            self.dependencies = 100
            self.install = target.mkdir
            self._make()
            self.assertEqual([
                I, "[%s] Start build.", target,
                I, "[%s] Build OK.", target,
            ], self._pop())
            self.assertEqual(self.uuid, self._make())
            self.assertEqual([
                I, "[%s] Already OK.", target,
            ], self._pop())
            self.dependencies = 101
            self.assertNotEqual(self.uuid, self._make())
            self.assertEqual([
                I, "[%s] Rebuild due to changed dependencies.", target,
                I, "[%s] Build OK.", target,
            ], self._pop())

    def test_fasterror(self):
        class X(Exception): pass
        def install():
            raise X
        with TemporaryDirectory() as tempdir:
            self.target = target = Path(tempdir, 'a')
            self.dependencies = None
            self.install = install
            with self.assertRaises(X):
                self._make()
            self.assertEqual([
                I, "[%s] Start build.", target,
            ], self._pop())
            with self.assertRaises(X):
                self._make()
            self.assertEqual([
                I, "[%s] Start build.", target,
            ], self._pop())

    def test_slowerror(self):
        class X(Exception): pass
        def install():
            target.mkdir()
            raise X
        with TemporaryDirectory() as tempdir:
            self.target = target = Path(tempdir, 'a')
            self.dependencies = None
            self.install = install
            with self.assertRaises(X):
                self._make()
            self.assertEqual([
                I, "[%s] Start build.", target,
            ], self._pop())
            with self.assertRaises(X):
                self._make()
            self.assertEqual([
                I, "[%s] Start build.", target,
                W, "[%s] Delete.", target,
            ], self._pop())

    def test_dirnotmade(self):
        with TemporaryDirectory() as tempdir:
            self.target = target = Path(tempdir, 'a')
            self.dependencies = None
            self.install = lambda: None
            with self.assertRaises(FileNotFoundError):
                self._make()
            self.assertEqual([
                I, "[%s] Start build.", target,
            ], self._pop())
            with self.assertRaises(FileNotFoundError):
                self._make()
            self.assertEqual([
                I, "[%s] Start build.", target,
            ], self._pop())
