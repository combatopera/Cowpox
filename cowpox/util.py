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

from chromalog.log import ColorizingFormatter, ColorizingStreamHandler
from collections.abc import Mapping
from diapyr import DI, types
from jproperties import Properties
import logging, networkx as nx, os, shutil

build_platform, = (f"{uname.sysname}-{uname.machine}".lower() for uname in [os.uname()])

class Logging:

    formatter = ColorizingFormatter("%(asctime)s [%(levelname)s] %(message)s")

    def __init__(self):
        logging.root.setLevel(logging.DEBUG)
        console = ColorizingStreamHandler()
        console.setLevel(logging.INFO)
        self._addhandler(console)

    def _addhandler(self, h):
        h.setFormatter(self.formatter)
        logging.root.addHandler(h)

    def setpath(self, logpath):
        self._addhandler(logging.FileHandler(logpath.pmkdirp()))

class DictView(Mapping):

    def __init__(self, obj):
        self.obj = obj

    def __getitem__(self, key):
        try:
            return getattr(self.obj, key)
        except AttributeError:
            raise KeyError(key)

    def __iter__(self):
        return iter(dir(self.obj))

    def __len__(self):
        return len(dir(self.obj))

def format_obj(format_string, obj):
    return format_string.format_map(DictView(obj))

def findimpls(module, basetype):
    g = nx.DiGraph()
    def add(c):
        if not g.has_node(c):
            for b in c.__bases__:
                g.add_edge(b, c)
                add(b)
    def isimpl(obj):
        try:
            return issubclass(obj, basetype)
        except TypeError:
            pass
    for obj in (getattr(module, name) for name in dir(module)):
        if isimpl(obj):
            add(obj)
    return (cls for cls, od in g.out_degree if not od)

class DIProxy: # TODO: Migrate to diapyr.

    @types(DI)
    def __init__(self, di):
        self.di = di

    def __getattr__(self, name):
        return getattr(self.di(self.targetclass), name)

def writeproperties(path, **kwargs):
    p = Properties()
    for k, v in kwargs.items():
        p[k] = v
    with path.open('wb') as f:
        p.store(f)

class Contrib:

    def __init__(self, srcdirs):
        self.srcdirs = srcdirs

    def filepaths(self):
        for relpath in sorted({path.relative_to(src) for src in self.srcdirs for path in src.rglob('*') if path.is_file()}):
            yield self.resolve(relpath), relpath

    def resolve(self, relpath):
        for src in self.srcdirs:
            path = src / relpath
            if path.is_file():
                return path

    def mergeinto(self, dst):
        for path, relpath in self.filepaths():
            dstpath = dst / relpath
            assert not dstpath.is_dir()
            shutil.copy2(path, dstpath.pmkdirp())

def coalesce(scope, *resolvables):
    for r in resolvables:
        obj = r.resolve(scope)
        try:
            if obj.scalar is not None:
                break
        except AttributeError:
            break
    return obj
