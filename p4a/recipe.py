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
from .boot import Bootstrap
from .python import HostPythonRecipe
from diapyr import types
from lagoon import find
from lagoon.program import Program
from pathlib import Path
from seizure.config import Config
import logging, os, subprocess

log = logging.getLogger(__name__)

class BootstrapNDKRecipe(Recipe):
    '''A recipe class for recipes built in an Android project jni dir with
    an Android.mk. These are not cached separatly, but built in the
    bootstrap's own building directory.

    To build an NDK project which is not part of the bootstrap, see
    :class:`~pythonforandroid.recipe.NDKRecipe`.

    To link with python, call the method :meth:`get_recipe_env`
    with the kwarg *with_python=True*.
    '''

    dir_name = None  # The name of the recipe build folder in the jni dir

    @types(Bootstrap)
    def __init(self, bootstrap):
        self.bootstrap = bootstrap

    def get_build_container_dir(self, arch):
        return self.get_jni_dir()

    def get_build_dir(self, arch):
        if self.dir_name is None:
            raise ValueError(f"{self.name} recipe doesn't define a dir_name, but this is necessary")
        return self.get_build_container_dir(arch) / self.dir_name

    def get_jni_dir(self):
        return self.bootstrap.build_dir / 'jni'

    def recipe_env_with_python(self, arch):
        env = super().get_recipe_env(arch)
        env['PYTHON_INCLUDE_ROOT'] = self.graph.python_recipe.include_root(arch)
        env['PYTHON_LINK_ROOT'] = self.graph.python_recipe.link_root(arch)
        env['EXTRA_LDLIBS'] = f" -lpython{self.graph.python_recipe.major_minor_version_string}"
        if 'python3' in self.graph.python_recipe.name:
            env['EXTRA_LDLIBS'] += 'm'
        return env

class NDKRecipe(Recipe):
    '''A recipe class for any NDK project not included in the bootstrap.'''

    generated_libraries = ()

    @types(Config)
    def __init(self, config):
        self.ndk_dir = Path(config.android_ndk_dir)
        self.ndk_api = config.android.ndk_api

    def should_build(self):
        lib_dir = self.get_lib_dir(self.arch)
        for lib in self.generated_libraries:
            if not (lib_dir / lib).exists():
                return True

    def get_lib_dir(self, arch):
        return self.get_build_dir(arch) / 'obj' / 'local' / arch.name

    def get_jni_dir(self, arch):
        return self.get_build_dir(arch) / 'jni'

    def build_arch(self):
        super().build_arch()
        Program.text(self.ndk_dir / 'ndk-build').print('V=1', f"APP_PLATFORM=android-{self.ndk_api}", f"APP_ABI={self.arch.name}",
                env = self.get_recipe_env(self.arch), cwd = self.get_build_dir(self.arch))

class PythonRecipe(Recipe):

    call_hostpython_via_targetpython = True
    '''If True, tries to install the module using the hostpython binary
    copied to the target (normally arm) python build dir. However, this
    will fail if the module tries to import e.g. _io.so. Set this to False
    to call hostpython from its own build dir, installing the module in
    the right place via arguments to setup.py. However, this may not set
    the environment correctly and so False is not the default.'''

    install_in_hostpython = False
    '''If True, additionally installs the module in the hostpython build
    dir. This will make it available to other recipes if
    call_hostpython_via_targetpython is False.
    '''

    install_in_targetpython = True
    '''If True, installs the module in the targetpython installation dir.
    This is almost always what you want to do.'''

    setup_extra_args = []
    '''List of extra arguments to pass to setup.py'''

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

    @types(HostPythonRecipe)
    def __init(self, hostrecipe):
        if not any(d for d in {'python2', 'python3', ('python2', 'python3')} if d in self.depends):
            # We ensure here that the recipe depends on python even it overrode
            # `depends`. We only do this if it doesn't already depend on any
            # python, since some recipes intentionally don't depend on/work
            # with all python variants
            depends = self.depends
            depends.append(('python2', 'python3'))
            self.depends = list(set(depends))
        self.hostrecipe = hostrecipe

    @property
    def real_hostpython_location(self):
        host_name = f"host{self.graph.python_recipe.name}"
        if host_name in {'hostpython2', 'hostpython3'}:
            return self.graph.get_recipe(host_name).python_exe
        else:
            return Path(f"python{self.graph.python_recipe.version}")

    @property
    def hostpython_location(self):
        return self.hostrecipe.python_exe if self.call_hostpython_via_targetpython else self.real_hostpython_location

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        env['PYTHONNOUSERSITE'] = '1'

        # Set the LANG, this isn't usually important but is a better default
        # as it occasionally matters how Python e.g. reads files
        env['LANG'] = "en_GB.UTF-8"

        if not self.call_hostpython_via_targetpython:
            python_name = self.graph.python_recipe.name
            env['CFLAGS'] += f" -I{self.graph.python_recipe.include_root(arch)}"
            env['LDFLAGS'] += f" -L{self.graph.python_recipe.link_root(arch)} -lpython{self.graph.python_recipe.major_minor_version_string}"
            if python_name == 'python3':
                env['LDFLAGS'] += 'm'
            hppath = []
            hppath.append(self.hostpython_location.parent / 'Lib')
            hppath.append(hppath[0] / 'site-packages')
            builddir = self.hostpython_location.parent / 'build'
            if builddir.exists():
                hppath.extend(d for d in builddir.iterdir() if d.is_dir())
            if hppath:
                if 'PYTHONPATH' in env:
                    env['PYTHONPATH'] = os.pathsep.join(map(str, [*hppath, env['PYTHONPATH']]))
                else:
                    env['PYTHONPATH'] = os.pathsep.join(map(str, hppath))
        return env

    def should_build(self):
        if self.ctx.insitepackages(self.name):
            log.info('Python package already exists in site-packages')
            return False
        log.info("%s apparently isn't already in site-packages", self.name)
        return True

    def build_arch(self):
        super().build_arch()
        self.install_python_package()

    def install_python_package(self):
        log.info("Installing %s into site-packages", self.name)
        Program.text(self.hostpython_location).print(
                'setup.py', 'install', '-O2', f"--root={self.ctx.get_python_install_dir()}", '--install-lib=.', *self.setup_extra_args,
                env = self.get_recipe_env(self.arch), cwd = self.get_build_dir(self.arch))
        if self.install_in_hostpython:
            self.install_hostpython_package()

    def get_hostrecipe_env(self, arch):
        return dict(os.environ, PYTHONPATH = self.real_hostpython_location.parent / 'Lib' / 'site-packages')

    def install_hostpython_package(self):
        env = self.get_hostrecipe_env(self.arch)
        Program.text(self.real_hostpython_location).print('setup.py', 'install', '-O2', f"--root={self.real_hostpython_location.parent}", '--install-lib=Lib/site-packages', *self.setup_extra_args, env = env, cwd = self.get_build_dir(self.arch))

class CompiledComponentsPythonRecipe(PythonRecipe):

    build_cmd = 'build_ext'

    def install_python_package(self):
        self.build_compiled_components()
        super().install_python_package()

    def build_compiled_components(self):
        log.info("Building compiled components in %s", self.name)
        env = self.get_recipe_env(self.arch)
        builddir = self.get_build_dir(self.arch)
        hostpython = Program.text(self.hostpython_location).partial(env = env, cwd = builddir)
        if self.install_in_hostpython:
            hostpython.print('setup.py', 'clean', '--all')
        hostpython.print('setup.py', self.build_cmd, '-v', *self.setup_extra_args)
        find.print(next(builddir.glob('build/lib.*')), '-name', '"*.o"', '-exec', env['STRIP'], '{}', ';', env = env, cwd = builddir)

    def install_hostpython_package(self):
        env = self.get_hostrecipe_env(self.arch)
        self.rebuild_compiled_components(env)
        super().install_hostpython_package()

    def rebuild_compiled_components(self, env):
        log.info("Rebuilding compiled components in %s", self.name)
        hostpython = Program.text(self.real_hostpython_location).partial(env = env, cwd = self.get_build_dir(self.arch))
        hostpython.print('setup.py', 'clean', '--all')
        hostpython.print('setup.py', self.build_cmd, '-v', *self.setup_extra_args)

class CythonRecipe(PythonRecipe):

    call_hostpython_via_targetpython = False

    @types(Bootstrap, HostPythonRecipe)
    def __init(self, bootstrap, hostrecipe):
        self.bootstrap = bootstrap
        self.hostrecipe = hostrecipe

    def install_python_package(self):
        log.info("Cythonizing anything necessary in %s", self.name)
        env = self.get_recipe_env(self.arch)
        builddir = self.get_build_dir(self.arch)
        hostpython = Program.text(self.hostrecipe.python_exe).partial(env = env, cwd = builddir)
        hostpython._c.print('import sys; print(sys.path)')
        log.info("Trying first build of %s to get cython files: this is expected to fail", self.name)
        manually_cythonise = False
        setup = hostpython.partial('setup.py', 'build_ext', '-v', *self.setup_extra_args)
        try:
            setup.print()
        except subprocess.CalledProcessError as e:
            if 1 != e.returncode:
                raise
            log.info("%s first build failed (as expected)", self.name)
            manually_cythonise = True
        if manually_cythonise:
            self.cythonize_build(env, builddir)
            setup.print()
        else:
            log.info('First build appeared to complete correctly, skipping manualcythonising.')
        self.strip_object_files(env, builddir)
        super().install_python_package()

    @staticmethod
    def strip_object_files(env, build_dir):
        log.info('Stripping object files')
        exec = find.partial('.', '-iname', '*.so', '-exec', env = env, cwd = build_dir)
        exec.print('echo', '{}', ';')
        exec.print(env['STRIP'].split(' ')[0], '--strip-unneeded', '{}', ';') # TODO: Avoid inspecting env.

    def cythonize_file(self, env, filename):
        log.info("Cythonize %s", filename)
        cyenv = env.copy()
        if 'CYTHONPATH' in cyenv:
            cyenv['PYTHONPATH'] = cyenv['CYTHONPATH']
        elif 'PYTHONPATH' in cyenv:
            del cyenv['PYTHONPATH']
        cyenv.pop('PYTHONNOUSERSITE', None)
        python_command = Program.text(f"python{self.graph.python_recipe.major_minor_version_string.split('.')[0]}")
        python_command.print("-m", "Cython.Build.Cythonize", filename, env = cyenv)

    def cythonize_build(self, env, build_dir):
        log.info('Running cython where appropriate')
        for filename in build_dir.rglob('*.pyx'):
            self.cythonize_file(env, filename)

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        env['LDFLAGS'] += f" -L{self.ctx.get_libs_dir(arch)} -L{self.ctx.libs_dir}  -L{self.bootstrap.build_dir / 'obj' / 'local' / arch.name} "
        env['LDSHARED'] = env['CC'] + ' -shared'
        env['LIBLINK'] = 'NOTNONE'
        env['NDKPLATFORM'] = self.platform.ndk_platform(arch)
        env['COPYLIBS'] = '1'
        env['LIBLINK_PATH'] = (self.get_build_container_dir(arch) / f"objects_{self.name}").mkdirp()
        return env
