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

from . import Arch, Graph, GraphInfo, InterpreterRecipe, LibRepo
from .config import Config
from .container import compileall
from .recipe import Recipe
from diapyr import types
from distutils.version import LooseVersion
from lagoon import cp, make
from lagoon.program import Program
from multiprocessing import cpu_count
from pathlib import Path
import logging, os, re

log = logging.getLogger(__name__)

class GuestPythonRecipe(Recipe, InterpreterRecipe, LibRepo):

    MIN_NDK_API = 21
    zlibversionpattern = re.compile('^#define ZLIB_VERSION "(.+)"$', re.MULTILINE)

    @types(Config, Arch, Graph, GraphInfo)
    def __init(self, config, arch, graph, graphinfo):
        self.ndk_dir = Path(config.NDK.dir)
        self.ndk_api = config.android.ndk_api
        self.use_lld = config.use.lld
        parts = LooseVersion(self.version).version
        self.majminversion = '.'.join(map(str, parts[:2]))
        self.pylibname = f"python{self.majminversion}m"
        self.instsoname = f"lib{self.pylibname}.so"
        self.androidbuild = self.recipebuilddir / 'android-build'
        self.modules_build_dir = self.androidbuild / 'build' / f"lib.linux-{arch.command_prefix.split('-')[0]}-{self.majminversion}"
        self.stdlibdir = self.recipebuilddir / 'Lib'
        self.graph = graph
        self.graphinfo = graphinfo

    def _set_libs_flags(self):
        env = os.environ.copy() # TODO: Probably redundant.
        env['HOSTARCH'] = self.arch.command_prefix
        env['CC'] = self.platform.clang_exe(self.arch, with_target = True)
        env['PATH'] = os.pathsep.join([str(self.platform.prebuiltbin(self.arch)), env['PATH']]) # XXX: Why prepend?
        env['CFLAGS'] = f"-fPIC -DANDROID -D__ANDROID_API__={self.ndk_api}"
        env['LDFLAGS'] = env.get('LDFLAGS', '')
        if self.use_lld:
            # Note: The -L. is to fix a bug in python 3.7.
            # https://bugs.freebsd.org/bugzilla/show_bug.cgi?id=234409
            env['LDFLAGS'] += ' -L. -fuse-ld=lld'
        else:
            log.warning('lld not enabled, linking without it. Consider installing lld if linker errors occur.')
        def aslist(key):
            return [env[key]] if key in env else []
        cppflags = aslist('CPPFLAGS')
        ldflags = aslist('LDFLAGS')
        libs = aslist('LIBS')
        def add_flags(include_flags, link_dirs, link_libs):
            cppflags.extend(f"-I{i}" for i in include_flags)
            ldflags.extend(f"-L{d}" for d in link_dirs)
            libs.extend(f"-l{l}" for l in link_libs)
        # XXX: Could we make install to somewhere to avoid much of this sort of thing?
        # TODO LATER: Use polymorphism!
        if 'sqlite3' in self.graphinfo.recipenames:
            log.info('Activating flags for sqlite3')
            add_flags(*self.graph.get_recipe('sqlite3').includeslinkslibs())
        if 'libffi' in self.graphinfo.recipenames:
            log.info('Activating flags for libffi')
            recipe = self.graph.get_recipe('libffi')
            env['PKG_CONFIG_PATH'] = recipe.recipebuilddir
            add_flags(*recipe.includeslinkslibs())
        if 'openssl' in self.graphinfo.recipenames:
            log.info('Activating flags for openssl')
            add_flags(*self.graph.get_recipe('openssl').includeslinkslibs())
        log.info('''Activating flags for android's zlib''')
        zlibinclude = self.ndk_dir / 'sysroot' / 'usr' / 'include'
        env['ZLIB_VERSION'] = self.zlibversionpattern.search((zlibinclude / 'zlib.h').read_text()).group(1)
        add_flags([zlibinclude], [self.platform.ndk_platform(self.arch) / 'usr' / 'lib'], ['z'])
        env['CPPFLAGS'] = ' '.join(cppflags)
        env['LDFLAGS'] = ' '.join(ldflags)
        env['LIBS'] = ' '.join(libs)
        return env

    def build_android(self, configure_args):
        assert self.ndk_api >= self.MIN_NDK_API
        self.androidbuild.mkdirp()
        env = self._set_libs_flags()
        Program.text(self.recipebuilddir / 'configure').print(*configure_args, env = env, cwd = self.androidbuild)
        make.all.print('-j', cpu_count(), f"INSTSONAME={self.instsoname}", env = env, cwd = self.androidbuild)
        cp.print(self.androidbuild / 'pyconfig.h', self.include_root())
        compileall(self.modules_build_dir)
        compileall(self.stdlibdir, False)

    def builtlibpaths(self):
        return [self.androidbuild / self.instsoname]

    def module_filens(self):
        return [*self.modules_build_dir.glob('*.so'), *self.modules_build_dir.glob('*.pyc')] # Recursion not needed.

    def include_root(self):
        return self.recipebuilddir / 'Include'

    def link_root(self):
        return self.androidbuild

    def recipe_env_with_python(self):
        env = self.arch.env.copy()
        env['PYTHON_INCLUDE_ROOT'] = self.include_root()
        env['PYTHON_LINK_ROOT'] = self.link_root()
        env['EXTRA_LDLIBS'] = f"-l{self.pylibname}"
        return env
