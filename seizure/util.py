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
from importlib import import_module
import logging, networkx as nx

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

class NoSuchPluginException(Exception): pass

def findimpls(modulename, basetype):
    try:
        module = import_module(modulename)
    except ModuleNotFoundError:
        raise NoSuchPluginException(modulename)
    g = nx.DiGraph()
    def add(cls):
        if not g.has_node(cls):
            for b in cls.__bases__:
                g.add_edge(b, cls)
                add(b)
    def accept(impl):
        try:
            return issubclass(impl, basetype)
        except TypeError:
            pass
    for impl in (getattr(module, name) for name in dir(module)):
        if accept(impl):
            add(impl)
    return (impl for impl, od in g.out_degree if not od)
