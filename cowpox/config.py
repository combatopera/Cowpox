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
from lagoon import git

def _githash(context, pathresolvable):
    return Text(git.rev_parse.__short.HEAD(cwd = pathresolvable.resolve(context).cat()).rstrip())

class Config:

    @classmethod
    def blank(cls):
        context = Context()
        context['githash',] = Function(_githash)
        with Repl(context) as repl:
            repl('container := $fork()') # TODO LATER: Bit of a hack.
        return cls(context, [])

    def __init__(self, context, prefix):
        self._context = context
        self._prefix = prefix

    def load(self, path):
        with Repl(self._context) as repl:
            repl.printf(f"""{''.join("%s " for _ in self._prefix)}. %s""", *self._prefix, path)

    def __getattr__(self, name):
        path = [*self._prefix, name]
        try:
            obj = self._context.resolved(*path)
        except NoSuchPathException:
            raise AttributeError(name) # XXX: Misleading?
        try:
            return obj.value # TODO: Does not work for all kinds of scalar.
        except AttributeError:
            return type(self)(self._context, path)

    def __setattr__(self, name, value):
        if name in {'_context', '_prefix'}:
            super().__setattr__(name, value)
        else:
            self._context[tuple([*self._prefix, name])] = Text(value)

    def _localcontext(self):
        return self._context.resolved(*self._prefix)

    def list(self):
        # TODO LATER: Should return Configs for non-scalars.
        return [o.value for _, o in self._localcontext().itero()]

    def dict(self): # XXX: Expose items instead?
        return {k: o.value for k, o in self._localcontext().itero()}

    def processtemplate(self, frompath, topath):
        with Repl(self._localcontext()) as repl:
            repl.printf("redirect %s", topath)
            repl.printf("< %s", frompath)
