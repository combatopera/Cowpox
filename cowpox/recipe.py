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

from . import Arch, Graph, GraphInfo
from .boot import Bootstrap
from .config import Config
from .mirror import Mirror
from .platform import Platform
from .python import HostPythonRecipe
from .util import format_obj
from diapyr import types
from lagoon import cp, find, patch as patchexe, tar, touch, unzip
from lagoon.program import Program
from pathlib import Path
from pkg_resources import resource_filename
from urllib.parse import urlparse
from zipfile import ZipFile
import hashlib, logging, os, shutil, subprocess

log = logging.getLogger(__name__)

class PluginType(type):

    def __init__(cls, *args):
        super().__init__(*args)
        fqmodule = cls.__module__
        cls.name = fqmodule[fqmodule.rfind('.') + 1:] # FIXME LATER: Do not override (possibly inherited) explicit name.

class Plugin(metaclass = PluginType): pass

class Recipe(Plugin):

    md5sum = None
    depends = []
    '''A list containing the names of any recipes that this recipe depends on.
    '''

    conflicts = []
    '''A list containing the names of any recipes that are known to be
    incompatible with this one.'''

    opt_depends = []
    '''A list of optional dependencies, that must be built before this
    recipe if they are built at all, but whose presence is not essential.'''
    patches = ()
    python_depends = []
    '''A list of pure-Python packages that this package requires. These
    packages will NOT be available at build time, but will be added to the
    list of pure-Python packages to install via pip. If you need these packages
    at build time, you must create a recipe.'''
    builtlibpaths = ()

    @classmethod
    def get_opt_depends_in_list(cls, recipenames):
        return [name for name in recipenames if name in cls.opt_depends]

    @property
    def url(self):
        return format_obj(self.urlformat, self)

    @property
    def dir_name(self):
        return self.name

    @types(Config, Platform, Graph, Mirror, Arch, GraphInfo)
    def __init__(self, config, platform, graph, mirror, arch, graphinfo):
        self.other_builds = Path(config.other_builds)
        self.projectbuilddir = Path(config.build.dir)
        self.extroot = Path(config.container.extroot)
        self.platform = platform
        self.graph = graph
        self.mirror = mirror
        self.arch = arch
        self.graphinfo = graphinfo

    def resourcepath(self, relpath):
        return Path(resource_filename(self.__module__, str(relpath)))

    def _extresourcepath(self, relpath):
        return Path(self.extroot, *self.__module__.split('.'), relpath)

    def apply_patch(self, relpath):
        log.info("Applying patch %s", relpath)
        patchexe._t._p1.print('-d', self.recipebuilddir, '-i', self.resourcepath(relpath))

    @property
    def buildcontainerparent(self):
        return self.other_builds / self.graphinfo.check_recipe_choices(self.name, [*self.depends, *([d] for d in self.opt_depends)])

    def get_build_container_dir(self):
        return self.buildcontainerparent / self.arch.builddirname()

    @property
    def recipebuilddir(self):
        return self.get_build_container_dir() / self.dir_name

    def download_if_necessary(self):
        if self.url is None:
            log.debug("[%s] Skip download as no URL is set.", self.name)
            return
        if not urlparse(self.url).scheme:
            log.debug("[%s] Skip download as URL is a path.", self.name)
            return
        log.info("[%s] Downloading.", self.name)
        path = self.mirror.download(self.url)
        if self.md5sum is not None:
            current_md5 = hashlib.md5(path.read_bytes()).hexdigest()
            if current_md5 != self.md5sum:
                log.debug("Generated md5sum: %s", current_md5)
                log.debug("Expected md5sum: %s", self.md5sum)
                raise ValueError(f"Generated md5sum does not match expected md5sum for {self.name} recipe")
            log.debug("[%s] MD5 OK.", self.name)

    def _copywithoutbuild(self, frompath, topath):
        try:
            frompath.relative_to(self.projectbuilddir)
        except ValueError:
            try:
                self.projectbuilddir.relative_to(frompath)
            except ValueError:
                ignore = None
            else:
                def ignore(dirpath, _):
                    if Path(dirpath) == self.projectbuilddir.parent:
                        log.debug("Not copying: %s", self.projectbuilddir)
                        return [self.projectbuilddir.name]
                    return []
            shutil.copytree(frompath, topath, ignore = ignore)
        else:
            log.warning("Refuse to copy %s descendant: %s", self.projectbuilddir, frompath)

    def prepare_build_dir(self):
        if self.url is None:
            log.debug("[%s] Skip unpack as no URL is set.", self.name)
            self.recipebuilddir.mkdir()
            return
        if not urlparse(self.url).scheme:
            srcpath = Path(self.url.replace('/', os.sep))
            log.info("[%s] Copy from: %s", self.name, srcpath)
            # TODO: Copy without .git either.
            self._copywithoutbuild(srcpath if srcpath.is_absolute() else self._extresourcepath(srcpath), self.recipebuilddir)
            return
        archivepath = self.mirror.getpath(self.url)
        log.info("[%s] Unpack for: %s", self.name, self.arch.name)
        # TODO LATER: Not such a good idea to use parent.
        # TODO LATER: Do not assume single top-level directory in archive.
        if self.url.endswith('.zip'):
            try:
                unzip.print(archivepath, cwd = self.recipebuilddir.parent)
            except subprocess.CalledProcessError as e:
                if e.returncode not in {1, 2}:
                    raise
            with ZipFile(archivepath) as zf:
                rootname = zf.filelist[0].filename.split('/')[0]
        elif self.url.endswith(('.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz')):
            tar.xf.print(archivepath, cwd = self.recipebuilddir.parent)
            rootname = tar.tf(archivepath).splitlines()[0].split('/')[0]
        else:
            raise Exception(f"Unsupported archive type: {self.url}")
        if rootname != self.recipebuilddir.name:
            self.recipebuilddir.with_name(rootname).rename(self.recipebuilddir)

    def get_recipe_env(self):
        env = self.arch.get_env()
        build_platform, = (f"{uname.sysname}-{uname.machine}".lower() for uname in [os.uname()])
        env['BUILDLIB_PATH'] = self.graph.get_recipe(f"host{self.graph.python_recipe.name}").recipebuilddir / 'native-build' / 'build' / f"lib.{build_platform}-{self.graph.python_recipe.majminversion}"
        return env

    def apply_patches(self):
        if self.patches:
            log.info("Applying patches for %s[%s]", self.name, self.arch.name)
            if (self.recipebuilddir / '.patched').exists():
                log.info("%s already patched, skipping", self.name)
                return
            for patch in self.patches:
                while True:
                    try:
                        acceptrecipe = patch.acceptrecipe
                    except AttributeError:
                        self.apply_patch(patch)
                        break
                    nextpatch = acceptrecipe(self)
                    if nextpatch is None:
                        log.debug("Patch denied: %s", patch)
                        break
                    patch = nextpatch
            touch.print(self.recipebuilddir / '.patched')

    def install_libraries(self):
        libs = [p for p in self._get_libraries() if p.name.endswith('.so')]
        if libs:
            cp.print(*libs, self.arch.libs_dir)

    def _get_libraries(self):
        return {self.recipebuilddir / libpath for libpath in self.builtlibpaths}

class BootstrapNDKRecipe(Recipe):

    @types(Config, Bootstrap)
    def __init(self, config, bootstrap):
        self.ndk_dir = Path(config.android_ndk_dir)
        self.jni_dir = bootstrap.build_dir / 'jni'
        self.bootstrap = bootstrap

    def get_build_container_dir(self):
        return self.jni_dir

    def recipe_env_with_python(self):
        env = super().get_recipe_env()
        env['PYTHON_INCLUDE_ROOT'] = self.graph.python_recipe.include_root()
        env['PYTHON_LINK_ROOT'] = self.graph.python_recipe.link_root()
        env['EXTRA_LDLIBS'] = f" -lpython{self.graph.python_recipe.majminversion}"
        if 'python3' in self.graph.python_recipe.name:
            env['EXTRA_LDLIBS'] += 'm'
        return env

    def ndk_build(self):
        Program.text(self.ndk_dir / 'ndk-build').print('V=1', env = self.get_recipe_env(), cwd = self.jni_dir)

class NDKRecipe(Recipe):

    @types(Config)
    def __init(self, config):
        self.ndk_dir = Path(config.android_ndk_dir)
        self.ndk_api = config.android.ndk_api

    def get_lib_dir(self):
        return self.recipebuilddir / 'obj' / 'local' / self.arch.name

    def ndk_build(self):
        Program.text(self.ndk_dir / 'ndk-build').print('V=1', f"APP_PLATFORM=android-{self.ndk_api}", f"APP_ABI={self.arch.name}",
                env = self.get_recipe_env(), cwd = self.recipebuilddir)

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

    @types(Config, HostPythonRecipe)
    def __init(self, config, hostrecipe):
        self.python_install_dir = Path(config.python_install_dir)
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
            return Path(f"python{self.graph.python_recipe.version}") # FIXME: Surely does not work.

    @property
    def hostpython_location(self):
        return self.hostrecipe.python_exe if self.call_hostpython_via_targetpython else self.real_hostpython_location

    def get_recipe_env(self):
        env = super().get_recipe_env()
        env['PYTHONNOUSERSITE'] = '1'

        # Set the LANG, this isn't usually important but is a better default
        # as it occasionally matters how Python e.g. reads files
        env['LANG'] = "en_GB.UTF-8"

        if not self.call_hostpython_via_targetpython:
            python_name = self.graph.python_recipe.name
            env['CFLAGS'] += f" -I{self.graph.python_recipe.include_root()}"
            env['LDFLAGS'] += f" -L{self.graph.python_recipe.link_root()} -lpython{self.graph.python_recipe.majminversion}"
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

    def install_python_package(self):
        log.info("Installing %s into site-packages", self.name)
        Program.text(self.hostpython_location).print(
                'setup.py', 'install', '-O2', f"--root={self.python_install_dir.pmkdirp()}", '--install-lib=.',
                env = self.get_recipe_env(), cwd = self.recipebuilddir)
        if self.install_in_hostpython:
            self.install_hostpython_package()

    def get_hostrecipe_env(self):
        return dict(os.environ, PYTHONPATH = self.real_hostpython_location.parent / 'Lib' / 'site-packages')

    def install_hostpython_package(self):
        env = self.get_hostrecipe_env()
        Program.text(self.real_hostpython_location).print('setup.py', 'install', '-O2', f"--root={self.real_hostpython_location.parent}", '--install-lib=Lib/site-packages', env = env, cwd = self.recipebuilddir)

class CompiledComponentsPythonRecipe(PythonRecipe):

    build_cmd = 'build_ext'

    def install_python_package(self):
        self.build_compiled_components()
        super().install_python_package()

    def build_compiled_components(self, *setup_extra_args):
        log.info("Building compiled components in %s", self.name)
        hostpython = Program.text(self.hostpython_location).partial(env = self.get_recipe_env(), cwd = self.recipebuilddir)
        if self.install_in_hostpython:
            hostpython.print('setup.py', 'clean', '--all')
        hostpython.print('setup.py', self.build_cmd, '-v', *setup_extra_args)
        objsdir, = self.recipebuilddir.glob('build/lib.*')
        find.print(objsdir, '-name', '*.o', '-exec', *self.arch.strip, '{}', ';')

    def install_hostpython_package(self):
        self.rebuild_compiled_components()
        super().install_hostpython_package()

    def rebuild_compiled_components(self, *setup_extra_args):
        env = self.get_hostrecipe_env()
        log.info("Rebuilding compiled components in %s", self.name)
        hostpython = Program.text(self.real_hostpython_location).partial(env = env, cwd = self.recipebuilddir)
        hostpython.print('setup.py', 'clean', '--all')
        hostpython.print('setup.py', self.build_cmd, '-v', *setup_extra_args)

class CythonRecipe(PythonRecipe):

    call_hostpython_via_targetpython = False

    @types(Config, Bootstrap, HostPythonRecipe)
    def __init(self, config, bootstrap, hostrecipe):
        self.libs_parent = config.libs_parent
        self.bootstrap = bootstrap
        self.hostrecipe = hostrecipe

    def install_python_package(self):
        log.info("Cythonizing anything necessary in %s", self.name)
        env = self.get_recipe_env()
        hostpython = Program.text(self.hostrecipe.python_exe).partial(env = env, cwd = self.recipebuilddir)
        hostpython._c.print('import sys; print(sys.path)')
        log.info("Trying first build of %s to get cython files: this is expected to fail", self.name)
        manually_cythonise = False
        setup = hostpython.partial('setup.py', 'build_ext')._v
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
        env['LDFLAGS'] += f" -L{self.arch.libs_dir} -L{self.libs_parent} -L{self.bootstrap.build_dir / 'obj' / 'local' / self.arch.name}"
        env['LDSHARED'] = env['CC'] + ' -shared'
        env['LIBLINK'] = 'NOTNONE'
        env['NDKPLATFORM'] = self.platform.ndk_platform(self.arch)
        env['COPYLIBS'] = '1'
        env['LIBLINK_PATH'] = (self.get_build_container_dir() / f"objects_{self.name}").mkdirp()
        return env
