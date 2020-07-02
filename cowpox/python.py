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

from . import GuestRecipe, HostRecipe
from .config import Config
from .recipe import Recipe
from diapyr import types
from distutils.version import LooseVersion
from lagoon import cp, make
from lagoon.program import Program
from multiprocessing import cpu_count
from pathlib import Path
import lagoon, logging, os, re

log = logging.getLogger(__name__)

class HostPythonRecipe(Recipe, HostRecipe): # XXX: Why does this exist at all?

    urlformat = "https://www.python.org/ftp/python/{version}/Python-{version}.tgz"

    @property
    def pythonexe(self):
        return Program.text(self.nativebuild / 'python')

    def get_build_container_dir(self):
        return self.buildcontainerparent / 'desktop'

    @property
    def nativebuild(self):
        return self.recipebuilddir / 'native-build'

    def build_exe(self):
        if not (self.nativebuild.mkdirp() / 'config.status').exists():
            Program.text(self.recipebuilddir / 'configure').print(cwd = self.nativebuild)
        setup_dist_location = self.recipebuilddir / 'Modules' / 'Setup.dist'
        if setup_dist_location.exists():
            cp.print(setup_dist_location, self.nativebuild / 'Modules' / 'Setup')
        else:
            setup_location = self.recipebuilddir / 'Modules' / 'Setup'
            if not setup_location.exists():
                raise Exception('Could not find Setup.dist or Setup in Python build')
        make.print('-j', cpu_count(), '-C', self.nativebuild, cwd = self.recipebuilddir)

    def compileall(self, dirpath, check = True):
        for path in dirpath.rglob('*.py'):
            os.utime(path, (0, 0)) # Determinism.
        self.pythonexe._OO._m.compileall._b._f.print(dirpath, check = check)

class GuestPythonRecipe(Recipe, GuestRecipe):

    MIN_NDK_API = 21
    opt_depends = ['sqlite3', 'libffi', 'openssl']
    '''The optional libraries which we would like to get our python linked'''
    zlibversionpattern = re.compile('^#define ZLIB_VERSION "(.+)"$', re.MULTILINE)

    @types(Config, HostRecipe)
    def __init(self, config, hostrecipe):
        self.ndk_dir = Path(config.android_ndk_dir)
        self.ndk_api = config.android.ndk_api
        parts = LooseVersion(self.version).version
        self.majversion = parts[0]
        self.majminversion = '.'.join(map(str, parts[:2]))
        self.exename = f"python{self.majversion}"
        self.pylibname = f"python{self.majminversion}{'m' if 3 == self.majversion else ''}"
        self.instsoname = f"lib{self.pylibname}.so"
        self.hostrecipe = hostrecipe

    def get_recipe_env(self):
        env = os.environ.copy()
        env['HOSTARCH'] = self.arch.command_prefix
        env['CC'] = self.platform.clang_exe(self.arch, with_target = True)
        env['PATH'] = os.pathsep.join([str(self.hostrecipe.nativebuild), str(self.platform.prebuiltbin(self.arch)), env['PATH']])
        env['CFLAGS'] = f"-fPIC -DANDROID -D__ANDROID_API__={self.ndk_api}"
        env['LDFLAGS'] = env.get('LDFLAGS', '')
        if hasattr(lagoon, 'lld'):
            # Note: The -L. is to fix a bug in python 3.7.
            # https://bugs.freebsd.org/bugzilla/show_bug.cgi?id=234409
            env['LDFLAGS'] += ' -L. -fuse-ld=lld'
        else:
            log.warning('lld not found, linking without it. Consider installing lld if linker errors occur.')
        return env

    def _set_libs_flags(self):
        env = self.get_recipe_env()
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

    @property
    def androidbuild(self):
        return self.recipebuilddir / 'android-build'

    def build_android(self, configure_args):
        assert self.ndk_api >= self.MIN_NDK_API
        self.androidbuild.mkdirp()
        env = self._set_libs_flags()
        Program.text(self.recipebuilddir / 'configure').print(*configure_args, env = env, cwd = self.androidbuild)
        make.all.print('-j', cpu_count(), f"INSTSONAME={self.instsoname}", env = env, cwd = self.androidbuild)
        cp.print(self.androidbuild / 'pyconfig.h', self.include_root())
        modules_build_dir = self.androidbuild / 'build' / f"lib.linux{2 if self.version[0] == '2' else ''}-{self.arch.command_prefix.split('-')[0]}-{self.majminversion}"
        self.hostrecipe.compileall(modules_build_dir)
        self.module_filens = [*modules_build_dir.glob('*.so'), *modules_build_dir.glob('*.pyc')] # Recursion not needed.
        self.stdlibdir = self.recipebuilddir / 'Lib'
        self.hostrecipe.compileall(self.stdlibdir, False)

    def include_root(self):
        return self.recipebuilddir / 'Include'

    def link_root(self):
        return self.androidbuild
