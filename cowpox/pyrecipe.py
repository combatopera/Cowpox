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

from . import InterpreterRecipe, ObjRepo
from .container import compileall
from .recipe import Recipe
from diapyr import types
from lagoon import python
from lagoon.program import partial
import logging, shutil, subprocess

log = logging.getLogger(__name__)

class PythonRecipe(Recipe):

    depends = ['python3']

    @types(InterpreterRecipe)
    def __init(self, interpreterrecipe):
        self.bundlepackages = self.recipebuilddir / 'Cowpox-bundle'
        self.interpreterrecipe = interpreterrecipe

    def get_recipe_env(self):
        env = self.arch.env.copy()
        env['PYTHONNOUSERSITE'] = '1'
        # Set the LANG, this isn't usually important but is a better default
        # as it occasionally matters how Python e.g. reads files
        env['LANG'] = "en_GB.UTF-8"
        env['CFLAGS'] += f" -I{self.interpreterrecipe.include_root()}"
        env['LDFLAGS'] += f" -L{self.interpreterrecipe.link_root()} -l{self.interpreterrecipe.pylibname}"
        return env

    def install_python_package(self, env = None):
        if env is None:
            env = self.get_recipe_env()
        log.info("Install %s into bundle.", self.name)
        rdir = self.bundlepackages / 'r'
        python[print]('setup.py', 'install', '-O2', '--root', rdir, '--install-lib', 'l', env = env, cwd = self.recipebuilddir)
        for p in (rdir / 'l').iterdir():
            p.rename(self.bundlepackages / p.name)
        shutil.rmtree(rdir)
        compileall(self.bundlepackages)

class CompiledComponentsPythonRecipe(PythonRecipe):

    build_ext_args = ()

    def install_python_package(self, env = None):
        if env is None:
            env = self.get_recipe_env()
        log.info("Building compiled components in %s", self.name)
        python[print]('setup.py', 'build_ext', '-v', *self.build_ext_args, env = env, cwd = self.recipebuilddir)
        self.striplibs() # FIXME LATER: Inexplicably leaves _bounded_integers.so unstripped.
        super().install_python_package(env)

class CythonRecipe(PythonRecipe):

    @types([ObjRepo])
    def __init(self, objrepos):
        self.objrepos = objrepos

    def install_python_package(self, env = None):
        if env is None:
            env = self.get_recipe_env()
        log.info("Cythonizing anything necessary in %s", self.name)
        log.info("Trying first build of %s to get cython files: this is expected to fail", self.name)
        manually_cythonise = False
        build_ext = python[partial]('setup.py', 'build_ext', env = env, cwd = self.recipebuilddir)._v
        try:
            build_ext[print]()
        except subprocess.CalledProcessError as e:
            if 1 != e.returncode:
                raise
            log.info("%s first build failed (as expected)", self.name)
            manually_cythonise = True
        if manually_cythonise:
            self.cythonize_build(env)
            log.info('Start build again.')
            build_ext[print]()
        else:
            log.info('First build appeared to complete correctly, skipping manualcythonising.')
        self.striplibs() # TODO: This breaks if host-arch libs are in the tree.
        super().install_python_package(env)

    def cythonize_build(self, env):
        log.info('Running Cython where appropriate.')
        env = env.copy()
        if 'CYTHONPATH' in env:
            env['PYTHONPATH'] = env['CYTHONPATH']
        elif 'PYTHONPATH' in env:
            del env['PYTHONPATH']
        env.pop('PYTHONNOUSERSITE', None)
        paths = list(self.pyxpaths())
        log.debug("Cythonize: %s", paths)
        python[print]('-m', 'Cython.Build.Cythonize', *paths, env = env)

    def pyxpaths(self):
        return self.recipebuilddir.rglob('*.pyx')

    def get_recipe_env(self):
        env = super().get_recipe_env()
        for objrepo in self.objrepos:
            env['LDFLAGS'] += f" -L{objrepo.recipebuilddir / 'obj' / 'local' / self.arch.name}"
        env['LDSHARED'] = env['CC'] + ' -shared'
        env['LIBLINK'] = 'NOTNONE'
        env['NDKPLATFORM'] = self.platform.ndk_platform(self.arch)
        env['COPYLIBS'] = '1'
        return env
