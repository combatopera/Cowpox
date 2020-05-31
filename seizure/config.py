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
    # FIXME: Do this without copying .git into container.
    return Text(git.rev_parse.__short.HEAD(cwd = pathresolvable.resolve(context).cat()).rstrip())

class Config:

    @classmethod
    def load(cls, path):
        context = Context()
        context['githash',] = Function(_githash)
        with Repl(context) as repl:
            repl.printf(". %s", path)
        return cls(context, [])

    def __init__(self, context, prefix):
        self._context = context
        self._prefix = prefix

    def __getattr__(self, name):
        path = [*self._prefix, name]
        try:
            obj = self._context.resolved(*path)
        except NoSuchPathException:
            raise AttributeError(name) # XXX: Misleading?
        try:
            return obj.value
        except AttributeError:
            return type(self)(self._context, path)

    def list(self):
        return [o.value for _, o in self._context.resolved(*self._prefix).itero()]

    def dict(self):
        return {k: o.value for k, o in self._context.resolved(*self._prefix).itero()}
