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

from aridimpl.model import Function, Text
from aridimpl.util import NoSuchPathException
from aridity import Context, Repl
from functools import partial
from importlib import import_module

undefined = object()

def pyref(context, moduleresolvable, qualnameresolvable):
    pyobj = import_module(moduleresolvable.resolve(context).cat())
    for name in qualnameresolvable.resolve(context).cat().split('.'):
        pyobj = getattr(pyobj, name)
    return Function(pyobj) # TODO LATER: Could be any type.

class Config: # TODO: Migrate to aridity as high-level API.

    @classmethod
    def blank(cls):
        c = Context()
        c['pyref',] = Function(pyref)
        return cls(c, [])

    def __init__(self, context, prefix):
        self._context = context
        self._prefix = prefix

    def load(self, path):
        with Repl(self._context) as repl:
            repl.printf(f"""{''.join("%s " for _ in self._prefix)}. %s""", *self._prefix, path)

    def exec(self, text):
        assert not self._prefix
        with Repl(self._context) as repl:
            for line in text.splitlines():
                repl(line)

    def __getattr__(self, name):
        path = [*self._prefix, name]
        try:
            obj = self._context.resolved(*path) # TODO LATER: Guidance for how lazy non-scalars should be in this situation.
        except NoSuchPathException:
            raise AttributeError(name) # XXX: Misleading?
        try:
            return obj.value # TODO: Does not work for all kinds of scalar.
        except AttributeError:
            return type(self)(self._context, path)

    def put(self, *path, function = undefined, text = undefined, resolvable = undefined):
        # TODO LATER: In theory we could add multiple types.
        factory, = (partial(t, v) for t, v in [[Function, function], [Text, text], [lambda x: x, resolvable]] if v is not undefined)
        self._context[tuple([*self._prefix, *path])] = factory()

    def _localcontext(self):
        return self._context.resolved(*self._prefix)

    def __iter__(self):
        for _, o in self.items():
            yield o

    def items(self):
        for k, o in self._localcontext().itero():
            try:
                yield k, o.value
            except AttributeError:
                yield k, type(self)(self._context, [*self._prefix, k])

    def processtemplate(self, frompath, topath):
        with Repl(self._localcontext()) as repl:
            repl.printf("redirect %s", topath)
            repl.printf("< %s", frompath)
