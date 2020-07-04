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

from . import HostRecipe
from .boot import Bootstrap
from .config import Config
from .container import compileall
from .recipe import Recipe
from diapyr import types
from lagoon import find, python
from lagoon.program import Program
import logging, os, shutil, subprocess

log = logging.getLogger(__name__)

class PythonRecipe(Recipe):

    call_hostpython_via_targetpython = True
    '''If True, tries to install the module using the hostpython binary
    copied to the target (normally arm) python build dir. However, this
    will fail if the module tries to import e.g. _io.so. Set this to False
    to call hostpython from its own build dir, installing the module in
    the right place via arguments to setup.py. However, this may not set
    the environment correctly and so False is not the default.'''
    depends = [('python2', 'python3')]
    '''
    .. note:: it's important to keep this depends as a class attribute outside
              `__init__` because sometimes we only initialize the class, so the
              `__init__` call won't be called and the deps would be missing
              (which breaks the dependency graph computation)

    .. warning:: don't forget to call `super().__init__()` in any recipe's
                 `__init__`, or otherwise it may not be ensured that it depends
                 on python2 or python3 which can break the dependency graph
    '''

    @types(Config, HostRecipe)
    def __init(self, config, hostrecipe):
        if not any(d for d in {'python2', 'python3', ('python2', 'python3')} if d in self.depends):
            # We ensure here that the recipe depends on python even it overrode
            # `depends`. We only do this if it doesn't already depend on any
            # python, since some recipes intentionally don't depend on/work
            # with all python variants
            depends = self.depends
            depends.append(('python2', 'python3'))
            self.depends = list(set(depends))
        self.hostrecipe = hostrecipe

    def get_recipe_env(self):
        env = super().get_recipe_env()
        env['PYTHONNOUSERSITE'] = '1'
        # Set the LANG, this isn't usually important but is a better default
        # as it occasionally matters how Python e.g. reads files
        env['LANG'] = "en_GB.UTF-8"
        if not self.call_hostpython_via_targetpython:
            env['CFLAGS'] += f" -I{self.graph.python_recipe.include_root()}"
            env['LDFLAGS'] += f" -L{self.graph.python_recipe.link_root()} -l{self.graph.python_recipe.pylibname}"
            hppath = []
            hppath.append(self.hostrecipe.nativebuild / 'Lib')
            hppath.append(hppath[0] / 'site-packages')
            builddir = self.hostrecipe.nativebuild / 'build'
            if builddir.exists():
                hppath.extend(d for d in builddir.iterdir() if d.is_dir())
            if hppath:
                if 'PYTHONPATH' in env:
                    env['PYTHONPATH'] = os.pathsep.join(map(str, [*hppath, env['PYTHONPATH']]))
                else:
                    env['PYTHONPATH'] = os.pathsep.join(map(str, hppath))
        return env

    def install_python_package(self):
        log.info("Install %s into bundle.", self.name)
        self.bundlepackages = self.recipebuilddir / 'Cowpox-bundle'
        rdir = self.bundlepackages / 'r'
        python.print('setup.py', 'install', '-O2', '--root', rdir, '--install-lib', 'l',
                env = self.get_recipe_env(), cwd = self.recipebuilddir)
        for p in (rdir / 'l').iterdir():
            p.rename(self.bundlepackages / p.name)
        shutil.rmtree(rdir)
        compileall(self.bundlepackages)

class CompiledComponentsPythonRecipe(PythonRecipe):

    def install_python_package(self):
        self.build_compiled_components()
        super().install_python_package()

    def build_compiled_components(self, *setup_extra_args):
        log.info("Building compiled components in %s", self.name)
        python.print('setup.py', 'build_ext', '-v', *setup_extra_args, env = self.get_recipe_env(), cwd = self.recipebuilddir)
        objsdir, = self.recipebuilddir.glob('build/lib.*')
        find.print(objsdir, '-name', '*.o', '-exec', *self.arch.strip, '{}', ';')

class CythonRecipe(PythonRecipe):

    call_hostpython_via_targetpython = False

    @types(Config, Bootstrap)
    def __init(self, config, bootstrap):
        self.bootstrap = bootstrap

    def install_python_package(self):
        log.info("Cythonizing anything necessary in %s", self.name)
        env = self.get_recipe_env()
        log.info("Trying first build of %s to get cython files: this is expected to fail", self.name)
        manually_cythonise = False
        setup = python.partial('setup.py', 'build_ext', env = env, cwd = self.recipebuilddir)._v
        try:
            setup.print()
        except subprocess.CalledProcessError as e:
            if 1 != e.returncode:
                raise
            log.info("%s first build failed (as expected)", self.name)
            manually_cythonise = True
        if manually_cythonise:
            self.cythonize_build(env, self.recipebuilddir)
            setup.print()
        else:
            log.info('First build appeared to complete correctly, skipping manualcythonising.')
        self.arch.strip_object_files(self.recipebuilddir)
        super().install_python_package()

    def cythonize_file(self, env, filename):
        log.info("Cythonize %s", filename)
        cyenv = env.copy()
        if 'CYTHONPATH' in cyenv:
            cyenv['PYTHONPATH'] = cyenv['CYTHONPATH']
        elif 'PYTHONPATH' in cyenv:
            del cyenv['PYTHONPATH']
        cyenv.pop('PYTHONNOUSERSITE', None)
        Program.text(self.graph.python_recipe.exename).print('-m', 'Cython.Build.Cythonize', filename, env = cyenv)

    def cythonize_build(self, env, build_dir):
        log.info('Running cython where appropriate')
        for filename in build_dir.rglob('*.pyx'):
            self.cythonize_file(env, filename)

    def get_recipe_env(self):
        env = super().get_recipe_env()
        env['LDFLAGS'] += f" -L{self.arch.libs_dir} -L{self.bootstrap.build_dir / 'obj' / 'local' / self.arch.name}"
        env['LDSHARED'] = env['CC'] + ' -shared'
        env['LIBLINK'] = 'NOTNONE'
        env['NDKPLATFORM'] = self.platform.ndk_platform(self.arch)
        env['COPYLIBS'] = '1'
        env['LIBLINK_PATH'] = (self.get_build_container_dir() / f"objects_{self.name}").mkdirp()
        return env
