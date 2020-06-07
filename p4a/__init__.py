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

from lagoon import cp, find, mv, patch as patchexe, rm, tar, touch, unzip
from lagoon.program import Program
from pathlib import Path
from pkg_resources import resource_filename
from seizure.util import format_obj
from urllib.parse import urlparse
from zipfile import ZipFile
import hashlib, logging, os, subprocess

log = logging.getLogger(__name__)

class Recipe:

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
    '''A list of patches to apply to the source. Values can be either a string
    referring to the patch file relative to the recipe dir, or a tuple of the
    string patch file and a callable, which will receive the kwargs `arch` and
    `recipe`, which should return True if the patch should be applied.'''

    python_depends = []
    '''A list of pure-Python packages that this package requires. These
    packages will NOT be available at build time, but will be added to the
    list of pure-Python packages to install via pip. If you need these packages
    at build time, you must create a recipe.'''
    builtlibpaths = ()

    @property
    def name(self):
        fqmodule = self._fqmodulename()
        return fqmodule[fqmodule.rfind('.') + 1:]

    @property
    def url(self):
        return format_obj(self.urlformat, self)

    def __init__(self, ctx):
        self.ctx = ctx

    def _fqmodulename(self):
        return type(self).__module__

    def resourcepath(self, relpath):
        return Path(resource_filename(self._fqmodulename(), str(relpath)))

    def apply_patch(self, relpath, arch):
        log.info("Applying patch %s", relpath)
        patchexe._t._p1.print('-d', self.get_build_dir(arch), '-i', self.resourcepath(relpath))

    def check_recipe_choices(self):
        '''Checks what recipes are being built to see which of the alternative
        and optional dependencies are being used,
        and returns a list of these.'''
        recipes = []
        built_recipes = self.ctx.recipe_build_order
        for recipe in self.depends:
            if isinstance(recipe, (tuple, list)):
                for alternative in recipe:
                    if alternative in built_recipes:
                        recipes.append(alternative)
                        break
        for recipe in self.opt_depends:
            if recipe in built_recipes:
                recipes.append(recipe)
        return sorted(recipes)

    def get_opt_depends_in_list(self, recipes):
        '''Given a list of recipe names, returns those that are also in
        self.opt_depends.
        '''
        return [recipe for recipe in recipes if recipe in self.opt_depends]

    def get_build_container_dir(self, arch):
        return self.ctx.other_builds / self.get_dir_name() / f"{arch.name}__ndk_target_{self.ctx.ndk_api}"

    def get_dir_name(self):
        choices = self.check_recipe_choices()
        dir_name = '-'.join([self.name] + choices)
        return dir_name

    def get_build_dir(self, arch):
        return self.get_build_container_dir(arch) / self.name

    def download_if_necessary(self, mirror):
        log.info("Downloading %s", self.name)
        user_dir = os.environ.get('P4A_{}_DIR'.format(self.name.lower()))
        if user_dir is not None:
            log.info("P4A_%s_DIR is set, skipping download for %s", self.name, self.name)
            return
        if self.url is None or not urlparse(self.url).scheme:
            log.info("Skipping %s download as no URL is set", self.name)
            return
        path = mirror.download(self.url)
        if self.md5sum is not None:
            current_md5 = hashlib.md5(path.read_bytes()).hexdigest()
            if current_md5 != self.md5sum:
                log.debug("Generated md5sum: %s", current_md5)
                log.debug("Expected md5sum: %s", self.md5sum)
                raise ValueError(f"Generated md5sum does not match expected md5sum for {self.name} recipe")
            log.debug("[%s] MD5 OK.", self.name)

    def _unpack(self, arch, mirror):
        directory_name = self.get_build_dir(arch)
        if self.url is not None and not urlparse(self.url).scheme:
            rm._rf.print(directory_name)
            cp._a.print(self.resourcepath(self.url.replace('/', os.sep)), directory_name)
            return
        log.info("Unpacking %s for %s", self.name, arch.name)
        build_dir = self.get_build_container_dir(arch)
        user_dir = os.environ.get(f"P4A_{self.name.lower()}_DIR")
        if user_dir is not None:
            log.info("P4A_%s_DIR exists, symlinking instead", self.name.lower())
            if not directory_name.exists():
                rm._rf.print(build_dir)
                build_dir.mkdirp()
                directory_name.symlink_to(user_dir)
            return
        if self.url is None:
            log.info("Skipping %s unpack as no URL is set", self.name)
            return
        if not directory_name.is_dir():
            extraction_filename = mirror.getpath(self.url)
            if self.url.endswith('.zip'):
                try:
                    unzip.print(extraction_filename, cwd = build_dir)
                except subprocess.CalledProcessError as e:
                    # return code 1 means unzipping had
                    # warnings but did complete,
                    # apparently happens sometimes with
                    # github zips
                    if e.returncode not in {1, 2}:
                        raise
                zf = ZipFile(extraction_filename, 'r')
                root_directory = zf.filelist[0].filename.split('/')[0]
                if root_directory != directory_name.name:
                    mv.print(root_directory, directory_name, cwd = build_dir)
            elif self.url.endswith(('.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz')):
                tar.xf.print(extraction_filename, cwd = build_dir)
                root_directory = tar.tf(extraction_filename).split('\n')[0].split('/')[0]
                if root_directory != directory_name.name:
                    mv.print(root_directory, directory_name, cwd = build_dir)
            else:
                raise Exception(f"Could not extract {extraction_filename} download, it must be .zip, .tar.gz or .tar.bz2 or .tar.xz")
        else:
            log.info("%s is already unpacked, skipping", self.name)

    def get_recipe_env(self, arch):
        return arch.get_env(self.ctx)

    def prebuild_arch(self, arch):
        pass

    def is_patched(self, arch):
        build_dir = self.get_build_dir(arch)
        return (build_dir / '.patched').exists()

    def apply_patches(self, arch):
        if self.patches:
            log.info("Applying patches for %s[%s]", self.name, arch.name)
            if self.is_patched(arch):
                log.info("%s already patched, skipping", self.name)
                return
            build_dir = self.get_build_dir(arch)
            for patch in self.patches:
                if isinstance(patch, (tuple, list)): # TODO: Yuk.
                    patch, patch_check = patch
                    if not patch_check(arch=arch, recipe=self):
                        continue
                self.apply_patch(patch, arch)
            touch.print(build_dir / '.patched')

    def should_build(self, arch):
        return not self.builtlibpaths or not all(p.exists() for p in self._get_libraries(arch)) # XXX: Weird logic?

    def build_arch(self, arch):
        build = f"build_{arch.name}"
        if hasattr(self, build):
            getattr(self, build)()

    def install_libraries(self, arch):
        self._install_libs(arch, [p for p in self._get_libraries(arch) if p.name.endswith('.so')])

    def postbuild_arch(self, arch):
        pass

    def prepare_build_dir(self, arch, mirror):
        self.get_build_container_dir(arch).mkdirp()
        self._unpack(arch, mirror)

    def _install_libs(self, arch, libs):
        if libs:
            cp.print(*libs, self.ctx.get_libs_dir(arch))

    def has_libs(self, arch, *libs):
        return all(map(lambda l: self.ctx.has_lib(arch, l), libs))

    def _get_libraries(self, arch):
        return {self.get_build_dir(arch) / libpath for libpath in self.builtlibpaths}

    def get_recipe(self, name):
        return self.ctx.get_recipe(name)

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

    def get_build_container_dir(self, arch):
        return self.get_jni_dir()

    def get_build_dir(self, arch):
        if self.dir_name is None:
            raise ValueError('{} recipe doesn\'t define a dir_name, but '
                             'this is necessary'.format(self.name))
        return self.get_build_container_dir(arch) / self.dir_name

    def get_jni_dir(self):
        return self.ctx.bootstrap.build_dir / 'jni'

    def recipe_env_with_python(self, arch):
        env = super().get_recipe_env(arch)
        env['PYTHON_INCLUDE_ROOT'] = self.ctx.python_recipe.include_root(arch)
        env['PYTHON_LINK_ROOT'] = self.ctx.python_recipe.link_root(arch)
        env['EXTRA_LDLIBS'] = ' -lpython{}'.format(self.ctx.python_recipe.major_minor_version_string)
        if 'python3' in self.ctx.python_recipe.name:
            env['EXTRA_LDLIBS'] += 'm'
        return env

class NDKRecipe(Recipe):
    '''A recipe class for any NDK project not included in the bootstrap.'''

    generated_libraries = []

    def should_build(self, arch):
        lib_dir = self.get_lib_dir(arch)
        for lib in self.generated_libraries:
            if not (lib_dir / lib).exists():
                return True
        return False

    def get_lib_dir(self, arch):
        return self.get_build_dir(arch) / 'obj' / 'local' / arch.name

    def get_jni_dir(self, arch):
        return self.get_build_dir(arch) / 'jni'

    def build_arch(self, arch, *extra_args):
        super().build_arch(arch)
        Program.text(self.ctx.ndk_dir / 'ndk-build').print('V=1', f"APP_PLATFORM=android-{self.ctx.ndk_api}", f"APP_ABI={arch.name}", *extra_args,
                env = self.get_recipe_env(arch), cwd = self.get_build_dir(arch))

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not any(d for d in {'python2', 'python3', ('python2', 'python3')} if d in self.depends):
            # We ensure here that the recipe depends on python even it overrode
            # `depends`. We only do this if it doesn't already depend on any
            # python, since some recipes intentionally don't depend on/work
            # with all python variants
            depends = self.depends
            depends.append(('python2', 'python3'))
            self.depends = list(set(depends))

    @property
    def real_hostpython_location(self):
        host_name = f"host{self.ctx.python_recipe.name}"
        if host_name in {'hostpython2', 'hostpython3'}:
            return self.get_recipe(host_name).python_exe
        else:
            return Path(f"python{self.ctx.python_recipe.version}")

    @property
    def hostpython_location(self):
        return self.ctx.hostpython if self.call_hostpython_via_targetpython else self.real_hostpython_location

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        env['PYTHONNOUSERSITE'] = '1'

        # Set the LANG, this isn't usually important but is a better default
        # as it occasionally matters how Python e.g. reads files
        env['LANG'] = "en_GB.UTF-8"

        if not self.call_hostpython_via_targetpython:
            python_name = self.ctx.python_recipe.name
            env['CFLAGS'] += ' -I{}'.format(
                self.ctx.python_recipe.include_root(arch)
            )
            env['LDFLAGS'] += ' -L{} -lpython{}'.format(
                self.ctx.python_recipe.link_root(arch),
                self.ctx.python_recipe.major_minor_version_string,
            )
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
                    env['PYTHONPATH'] = ':'.join(map(str, hppath + [env['PYTHONPATH']]))
                else:
                    env['PYTHONPATH'] = ':'.join(map(str, hppath))
        return env

    def should_build(self, arch):
        if self.ctx.insitepackages(self.name):
            log.info('Python package already exists in site-packages')
            return False
        log.info("%s apparently isn't already in site-packages", self.name)
        return True

    def build_arch(self, arch):
        super().build_arch(arch)
        self.install_python_package(arch)

    def install_python_package(self, arch):
        name = self.name
        env = self.get_recipe_env(arch)
        log.info("Installing %s into site-packages", self.name)
        builddir = self.get_build_dir(arch)
        hostpython = Program.text(self.hostpython_location)
        hpenv = env.copy()
        hostpython.print('setup.py', 'install', '-O2', f"--root={self.ctx.get_python_install_dir()}", '--install-lib=.', *self.setup_extra_args, env = hpenv, cwd = builddir)
        if self.install_in_hostpython:
            self.install_hostpython_package(arch)

    def get_hostrecipe_env(self, arch):
        return dict(os.environ, PYTHONPATH = self.real_hostpython_location.parent / 'Lib' / 'site-packages')

    def install_hostpython_package(self, arch):
        env = self.get_hostrecipe_env(arch)
        Program.text(self.real_hostpython_location).print('setup.py', 'install', '-O2', f"--root={self.real_hostpython_location.parent}", '--install-lib=Lib/site-packages', *self.setup_extra_args, env = env, cwd = self.get_build_dir(arch))

class CompiledComponentsPythonRecipe(PythonRecipe):

    pre_build_ext = False
    build_cmd = 'build_ext'

    def install_python_package(self, arch):
        self.build_compiled_components(arch)
        super().install_python_package(arch)

    def build_compiled_components(self, arch):
        log.info("Building compiled components in %s", self.name)
        env = self.get_recipe_env(arch)
        builddir = self.get_build_dir(arch)
        hostpython = Program.text(self.hostpython_location).partial(env = env, cwd = builddir)
        if self.install_in_hostpython:
            hostpython.print('setup.py', 'clean', '--all')
        hostpython.print('setup.py', self.build_cmd, '-v', *self.setup_extra_args)
        find.print(next(builddir.glob('build/lib.*')), '-name', '"*.o"', '-exec', env['STRIP'], '{}', ';', env = env, cwd = builddir)

    def install_hostpython_package(self, arch):
        env = self.get_hostrecipe_env(arch)
        self.rebuild_compiled_components(arch, env)
        super().install_hostpython_package(arch)

    def rebuild_compiled_components(self, arch, env):
        log.info("Rebuilding compiled components in %s", self.name)
        hostpython = Program.text(self.real_hostpython_location).partial(env = env, cwd = self.get_build_dir(arch))
        hostpython.print('setup.py', 'clean', '--all')
        hostpython.print('setup.py', self.build_cmd, '-v', *self.setup_extra_args)

class CythonRecipe(PythonRecipe):

    pre_build_ext = False
    cythonize = True
    cython_args = []
    call_hostpython_via_targetpython = False

    def install_python_package(self, arch):
        self._build_cython_components(arch)
        super().install_python_package(arch)

    def _build_cython_components(self, arch):
        log.info("Cythonizing anything necessary in %s", self.name)
        env = self.get_recipe_env(arch)
        builddir = self.get_build_dir(arch)
        hostpython = Program.text(self.ctx.hostpython).partial(env = env, cwd = builddir)
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
        python_command = Program.text(f"python{self.ctx.python_recipe.major_minor_version_string.split('.')[0]}")
        python_command.print("-m", "Cython.Build.Cythonize", filename, *self.cython_args, env = cyenv)

    def cythonize_build(self, env, build_dir):
        if not self.cythonize:
            log.info('Running cython cancelled per recipe setting')
            return
        log.info('Running cython where appropriate')
        for filename in build_dir.rglob('*.pyx'):
            self.cythonize_file(env, filename)

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        env['LDFLAGS'] += f" -L{self.ctx.get_libs_dir(arch)} -L{self.ctx.libs_dir}  -L{self.ctx.bootstrap.build_dir / 'obj' / 'local' / arch.name} "
        env['LDSHARED'] = env['CC'] + ' -shared'
        env['LIBLINK'] = 'NOTNONE'
        env['NDKPLATFORM'] = self.ctx.ndk_platform
        env['COPYLIBS'] = '1'
        env['LIBLINK_PATH'] = str((self.get_build_container_dir(arch) / f"objects_{self.name}").mkdirp())
        return env
