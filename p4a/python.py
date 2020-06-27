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

from . import Recipe
from cowpox.config import Config
from diapyr import types
from distutils.version import LooseVersion
from fnmatch import fnmatch
from lagoon import cp, find, make, mv, zip
from lagoon.program import Program
from multiprocessing import cpu_count
from pathlib import Path
from shutil import copy2
import lagoon, logging, os, re

log = logging.getLogger(__name__)

def _walk_valid_filens(base_dir, invalid_dir_names, invalid_file_patterns):
    for dirn, subdirs, filens in os.walk(base_dir):
        for i in reversed(range(len(subdirs))):
            subdir = subdirs[i]
            if subdir in invalid_dir_names:
                subdirs.pop(i)
        for filen in filens:
            for pattern in invalid_file_patterns:
                if fnmatch(filen, pattern):
                    break
            else:
                yield Path(dirn, filen)

class HostPythonRecipe(Recipe):

    build_subdir = 'native-build'
    urlformat = "https://www.python.org/ftp/python/{version}/Python-{version}.tgz"

    @property
    def python_exe(self):
        return self.get_path_to_python() / f"python{self.version.split('.')[0]}"

    def should_build(self):
        return not self.python_exe.exists()

    def get_build_container_dir(self):
        return self.buildcontainerparent / 'desktop'

    def get_path_to_python(self):
        return self.get_build_dir() / self.build_subdir

    def build_arch(self):
        recipe_build_dir = self.get_build_dir()
        build_dir = (recipe_build_dir / self.build_subdir).mkdirp()
        if not (build_dir / 'config.status').exists():
            Program.text(recipe_build_dir / 'configure').print(cwd = build_dir)
        setup_dist_location = recipe_build_dir / 'Modules' / 'Setup.dist'
        if setup_dist_location.exists():
            cp.print(setup_dist_location, build_dir / 'Modules' / 'Setup')
        else:
            setup_location = recipe_build_dir / 'Modules' / 'Setup'
            if not setup_location.exists():
                raise Exception('Could not find Setup.dist or Setup in Python build')
        make.print('-j', cpu_count(), '-C', build_dir, cwd = recipe_build_dir)
        exe, = (exe for exe in (self.get_path_to_python() / exe_name for exe_name in ['python.exe', 'python']) if exe.is_file())
        cp.print(exe, self.python_exe)

class GuestPythonRecipe(Recipe):

    MIN_NDK_API = 21
    configure_args = ()
    '''The configure arguments needed to build the python recipe. Those are
    used in method :meth:`build_arch` (if not overwritten like python3's
    recipe does).

    .. note:: This variable should be properly set in subclass.
    '''

    stdlib_dir_blacklist = {
        '__pycache__',
        'test',
        'tests',
        'lib2to3',
        'ensurepip',
        'idlelib',
        'tkinter',
    }
    '''The directories that we want to omit for our python bundle'''

    stdlib_filen_blacklist = [
        '*.py',
        '*.exe',
        '*.whl',
    ]
    '''The file extensions that we want to blacklist for our python bundle'''

    site_packages_dir_blacklist = {
        '__pycache__',
        'tests'
    }
    '''The directories from site packages dir that we don't want to be included
    in our python bundle.'''

    site_packages_filen_blacklist = [
        '*.py'
    ]
    '''The file extensions from site packages dir that we don't want to be
    included in our python bundle.'''

    opt_depends = ['sqlite3', 'libffi', 'openssl']
    '''The optional libraries which we would like to get our python linked'''

    compiled_extension = '.pyc'
    '''the default extension for compiled python files.

    .. note:: the default extension for compiled python files has been .pyo for
        python 2.x-3.4 but as of Python 3.5, the .pyo filename extension is no
        longer used and has been removed in favour of extension .pyc
    '''
    zlibversionpattern = re.compile('^#define ZLIB_VERSION "(.+)"$', re.MULTILINE)

    @types(Config, HostPythonRecipe)
    def __init(self, config, hostrecipe):
        self.python_install_dir = Path(config.python_install_dir)
        self.ndk_dir = Path(config.android_ndk_dir)
        self.android_project_dir = Path(config.android.project.dir)
        self.ndk_api = config.android.ndk_api
        parts = LooseVersion(self.version).version
        self.majversion = parts[0]
        self.majminversion = '.'.join(map(str, parts[:2]))
        self.exename = f"python{self.majversion}"
        self.hostrecipe = hostrecipe

    def get_recipe_env(self):
        env = os.environ.copy()
        env['HOSTARCH'] = self.arch.command_prefix
        env['CC'] = self.platform.clang_exe(self.arch, with_target = True)
        env['PATH'] = os.pathsep.join([f"""{self.graph.get_recipe(f"host{self.name}").get_path_to_python()}""", str(self.platform.prebuiltbin(self.arch)), env['PATH']])
        env['CFLAGS'] = f"-fPIC -DANDROID -D__ANDROID_API__={self.ndk_api}"
        env['LDFLAGS'] = env.get('LDFLAGS', '')
        if hasattr(lagoon, 'lld'):
            # Note: The -L. is to fix a bug in python 3.7.
            # https://bugs.freebsd.org/bugzilla/show_bug.cgi?id=234409
            env['LDFLAGS'] += ' -L. -fuse-ld=lld'
        else:
            log.warning('lld not found, linking without it. Consider installing lld if linker errors occur.')
        return env

    def set_libs_flags(self, env):
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
            env['PKG_CONFIG_PATH'] = recipe.get_build_dir()
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
    def _libpython(self):
        '''return the python's library name (with extension)'''
        py_version = self.majminversion
        if self.majversion == 3:
            py_version += 'm'
        return f"libpython{py_version}.so"

    def should_build(self):
        return not (self.link_root() / self._libpython).is_file()

    def build_arch(self):
        assert self.ndk_api >= self.MIN_NDK_API
        recipe_build_dir = self.get_build_dir()
        build_dir = (recipe_build_dir / 'android-build').mkdirp()
        sys_prefix = '/usr/local'
        sys_exec_prefix = '/usr/local'
        env = self.set_libs_flags(self.get_recipe_env())
        android_build = Program.text(recipe_build_dir / 'config.guess')(cwd = build_dir).strip()
        if not (build_dir / 'config.status').exists():
            kwargs = dict(android_host = env['HOSTARCH'], android_build = android_build, prefix = sys_prefix, exec_prefix = sys_exec_prefix)
            configureargs = [a.format(**kwargs) for a in self.configure_args] # TODO: Use format_obj.
            Program.text(recipe_build_dir / 'configure').print(*configureargs, env = env, cwd = build_dir)
        make.print('all', '-j', cpu_count(), f"INSTSONAME={self._libpython}", env = env, cwd = build_dir)
        cp.print(build_dir / 'pyconfig.h', recipe_build_dir / 'Include')

    def include_root(self):
        return self.get_build_dir() / 'Include'

    def link_root(self):
        return self.get_build_dir() / 'android-build'

    def _compile_python_files(self, dirpath):
        args = ['-b'] if self.name == 'python3' else [] # XXX: Simplify?
        # TODO: Duplicated code.
        for path in dirpath.rglob('*.py'):
            os.utime(path, (0, 0)) # Determinism.
        Program.text(self.hostrecipe.python_exe)._OO._m.compileall.print(*args, '-f', dirpath, check = False) # XXX: Why not check?

    def create_python_bundle(self):
        dirn = (self.android_project_dir / '_python_bundle' / '_python_bundle').mkdirp()
        modules_build_dir = self.get_build_dir() / 'android-build' / 'build' / f"lib.linux{2 if self.version[0] == '2' else ''}-{self.arch.command_prefix.split('-')[0]}-{self.majminversion}"
        self._compile_python_files(dirn / modules_build_dir)
        self._compile_python_files(dirn / self.get_build_dir() / 'Lib')
        self._compile_python_files(dirn / self.python_install_dir)
        modules_dir = (dirn / 'modules').mkdirp()
        c_ext = self.compiled_extension
        module_filens = [*modules_build_dir.glob('*.so'), *modules_build_dir.glob(f"*{c_ext}")]
        log.info("Copy %s files into the bundle", len(module_filens))
        for filen in module_filens:
            log.info(" - copy %s", filen)
            copy2(filen, modules_dir)
        stdlib_zip = dirn / 'stdlib.zip'
        libdir = self.get_build_dir() / 'Lib'
        stdlib_filens = list(_walk_valid_filens(libdir, self.stdlib_dir_blacklist, self.stdlib_filen_blacklist))
        log.info("Zip %s files into the bundle", len(stdlib_filens))
        zip.print(stdlib_zip, *(p.relative_to(libdir) for p in stdlib_filens), cwd = libdir)
        (dirn / 'site-packages').mkdirp()
        installdir = self.python_install_dir.mkdirp()
        filens = list(_walk_valid_filens(installdir, self.site_packages_dir_blacklist, self.site_packages_filen_blacklist))
        log.info("Copy %s files into the site-packages", len(filens))
        for filen in filens:
            log.info(" - copy %s", filen)
            copy2(filen, (dirn / 'site-packages' / filen.relative_to(installdir)).pmkdirp())
        python_lib_name = f"libpython{self.majminversion}"
        if self.majversion == 3:
            python_lib_name += 'm'
        cp.print(self.get_build_dir() / 'android-build' / f"{python_lib_name}.so", self.android_project_dir / 'libs' / self.arch.name)
        log.info('Renaming .so files to reflect cross-compile')
        self._reduce_object_file_names(dirn / 'site-packages')
        return dirn / 'site-packages'

    def _reduce_object_file_names(self, dirn):
        """Recursively renames all files named YYY.cpython-...-linux-gnu.so"
        to "YYY.so", i.e. removing the erroneous architecture name
        coming from the local system.
        """
        for filen in map(Path, find(dirn, '-iname', '*.so').splitlines()):
            parts = filen.name.split('.')
            if len(parts) > 2:
                mv.print(filen, filen.parent / f"{parts[0]}.so")
