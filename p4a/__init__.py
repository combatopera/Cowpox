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

from distutils.version import LooseVersion
from lagoon import basename, cp, find, git as sysgit, mkdir, mv, patch as patchexe, rm, rmdir, tar, touch, unzip
from lagoon.program import Program
from os.path import join, split
from pathlib import Path
from pythonforandroid.util import current_directory
from seizure.mirror import Mirror
from urllib.parse import urlparse
from zipfile import ZipFile
import hashlib, logging, os, re, shutil, subprocess

log = logging.getLogger(__name__)

class RecipeMeta(type):

    def __new__(cls, name, bases, dct):
        if name != 'Recipe':
            if 'url' in dct:
                dct['_url'] = dct.pop('url')
            if 'version' in dct:
                dct['_version'] = dct.pop('version')
        return super(RecipeMeta, cls).__new__(cls, name, bases, dct)

class Recipe(metaclass = RecipeMeta):

    build_platform = f"{os.uname()[0]}-{os.uname()[-1]}".lower()
    _url = None
    '''The address from which the recipe may be downloaded. This is not
    essential, it may be omitted if the source is available some other
    way, such as via the :class:`IncludedFilesBehaviour` mixin.

    If the url includes the version, you may (and probably should)
    replace this with ``{version}``, which will automatically be
    replaced by the :attr:`version` string during download.

    .. note:: Methods marked (internal) are used internally and you
              probably don't need to call them, but they are available
              if you want.
    '''

    _version = None
    '''A string giving the version of the software the recipe describes,
    e.g. ``2.0.3`` or ``master``.'''

    md5sum = None
    '''The md5sum of the source from the :attr:`url`. Non-essential, but
    you should try to include this, it is used to check that the download
    finished correctly.
    '''

    depends = []
    '''A list containing the names of any recipes that this recipe depends on.
    '''

    conflicts = []
    '''A list containing the names of any recipes that are known to be
    incompatible with this one.'''

    opt_depends = []
    '''A list of optional dependencies, that must be built before this
    recipe if they are built at all, but whose presence is not essential.'''

    patches = []
    '''A list of patches to apply to the source. Values can be either a string
    referring to the patch file relative to the recipe dir, or a tuple of the
    string patch file and a callable, which will receive the kwargs `arch` and
    `recipe`, which should return True if the patch should be applied.'''

    python_depends = []
    '''A list of pure-Python packages that this package requires. These
    packages will NOT be available at build time, but will be added to the
    list of pure-Python packages to install via pip. If you need these packages
    at build time, you must create a recipe.'''

    archs = ['armeabi']  # Not currently implemented properly

    built_libraries = {}
    """Each recipe that builds a system library (e.g.:libffi, openssl, etc...)
    should contain a dict holding the relevant information of the library. The
    keys should be the generated libraries and the values the relative path of
    the library inside his build folder. This dict will be used to perform
    different operations:
        - copy the library into the right location, depending on if it's shared
          or static)
        - check if we have to rebuild the library

    Here an example of how it would look like for `libffi` recipe:

        - `built_libraries = {'libffi.so': '.libs'}`

    .. note:: in case that the built library resides in recipe's build
              directory, you can set the following values for the relative
              path: `'.', None or ''`
    """

    need_stl_shared = False
    '''Some libraries or python packages may need to be linked with android's
    stl. We can automatically do this for any recipe if we set this property to
    `True`'''

    stl_lib_name = 'c++_shared'
    '''
    The default STL shared lib to use: `c++_shared`.

    .. note:: Android NDK version > 17 only supports 'c++_shared', because
        starting from NDK r18 the `gnustl_shared` lib has been deprecated.
    '''

    stl_lib_source = '{ctx.ndk_dir}/sources/cxx-stl/llvm-libc++'
    '''
    The source directory of the selected stl lib, defined in property
    `stl_lib_name`
    '''

    def __init__(self, ctx):
        self.ctx = ctx

    @property
    def stl_include_dir(self):
        return join(self.stl_lib_source.format(ctx=self.ctx), 'include')

    def get_stl_lib_dir(self, arch):
        return join(
            self.stl_lib_source.format(ctx=self.ctx), 'libs', arch.arch
        )

    def get_stl_library(self, arch):
        return join(
            self.get_stl_lib_dir(arch),
            'lib{name}.so'.format(name=self.stl_lib_name),
        )

    def install_stl_lib(self, arch):
        if not self.ctx.has_lib(
            arch.arch, 'lib{name}.so'.format(name=self.stl_lib_name)
        ):
            self.install_libs(arch, self.get_stl_library(arch))

    @property
    def version(self):
        key = 'VERSION_' + self.name
        return os.environ.get(key, self._version)

    @property
    def url(self):
        key = 'URL_' + self.name
        return os.environ.get(key, self._url)

    @property
    def versioned_url(self):
        '''A property returning the url of the recipe with ``{version}``
        replaced by the :attr:`url`. If accessing the url, you should use this
        property, *not* access the url directly.'''
        if self.url is None:
            return None
        return self.url.format(version=self.version)

    def download_file(self, url, target):
        if not url:
            return
        log.info("Downloading %s from %s", self.name, url)
        parsed_url = urlparse(url)
        if parsed_url.scheme in {'http', 'https'}:
            if target.exists():
                target.unlink()
            target.symlink_to(Mirror.download(url))
            return target
        elif parsed_url.scheme in {'git', 'git+file', 'git+ssh', 'git+http', 'git+https'}:
            if target.is_dir():
                git = sysgit.partial(cwd = target)
                git.fetch.__tags.print()
                if self.version:
                    git.checkout.print(self.version)
                git.pull.print()
                git.pull.__recurse_submodules.print()
                git.submodule.update.__recursive.print()
            else:
                if url.startswith('git+'):
                    url = url[4:]
                sysgit.clone.__recursive.print(url, target)
                if self.version:
                    git = sysgit.partial(cwd = target)
                    git.checkout.print(self.version)
                    git.submodule.update.__recursive.print()
            return target

    def apply_patch(self, filename, arch, build_dir = None):
        log.info("Applying patch %s", filename)
        patchexe._t._p1.print('-d', build_dir if build_dir else self.get_build_dir(arch), '-i', self.get_recipe_dir() / filename)

    def copy_file(self, filename, dest):
        log.info("Copy %s to %s", filename, dest)
        filename = join(self.get_recipe_dir(), filename)
        dest = join(self.build_dir, dest)
        shutil.copy(filename, dest)

    def append_file(self, filename, dest):
        log.info("Append %s to %s", filename, dest)
        filename = join(self.get_recipe_dir(), filename)
        dest = join(self.build_dir, dest)
        with open(filename, "rb") as fd:
            data = fd.read()
        with open(dest, "ab") as fd:
            fd.write(data)

    @property
    def name(self):
        '''The name of the recipe, the same as the folder containing it.'''
        modname = self.__class__.__module__
        return modname.split(".", 2)[-1]

    @property
    def filtered_archs(self):
        '''Return archs of self.ctx that are valid build archs
        for the Recipe.'''
        result = []
        for arch in self.ctx.archs:
            if not self.archs or (arch.arch in self.archs):
                result.append(arch)
        return result

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
        return self.ctx.buildsdir / 'other_builds' / self.get_dir_name() / f"{arch}__ndk_target_{self.ctx.ndk_api}"

    def get_dir_name(self):
        choices = self.check_recipe_choices()
        dir_name = '-'.join([self.name] + choices)
        return dir_name

    def get_build_dir(self, arch):
        return self.get_build_container_dir(arch) / self.name

    def get_recipe_dir(self):
        local_recipe_dir = self.ctx.local_recipes / self.name
        if local_recipe_dir.exists():
            return local_recipe_dir
        return self.ctx.contribroot / 'recipes' / self.name

    def download_if_necessary(self):
        log.info("Downloading %s", self.name)
        user_dir = os.environ.get('P4A_{}_DIR'.format(self.name.lower()))
        if user_dir is not None:
            log.info("P4A_%s_DIR is set, skipping download for %s", self.name, self.name)
            return
        self.download()

    def download(self):
        if self.url is None:
            log.info("Skipping %s download as no URL is set", self.name)
            return
        url = self.versioned_url
        ma = re.match('^(.+)#md5=([0-9a-f]{32})$', url)
        if ma:                  # fragmented URL?
            if self.md5sum:
                raise ValueError(
                    ('Received md5sum from both the {} recipe '
                     'and its url').format(self.name))
            url = ma.group(1)
            expected_md5 = ma.group(2)
        else:
            expected_md5 = self.md5sum
        mkdir._p.print(self.ctx.packages_path / self.name)
        with current_directory(self.ctx.packages_path / self.name):
            filename = Path(basename(url)[:-1])
            do_download = True
            marker_filename = Path(f".mark-{filename}")
            if filename.exists() and filename.is_file():
                if not marker_filename.exists():
                    rm.print(filename)
                elif expected_md5:
                    current_md5 = _md5sum(filename)
                    if current_md5 != expected_md5:
                        log.debug("Generated md5sum: %s", current_md5)
                        log.debug("Expected md5sum: %s", expected_md5)
                        raise ValueError(
                            ('Generated md5sum does not match expected md5sum '
                             'for {} recipe').format(self.name))
                    do_download = False
                else:
                    do_download = False

            # If we got this far, we will download
            if do_download:
                log.debug("Downloading %s from %s", self.name, url)
                rm._f.print(marker_filename)
                self.download_file(self.versioned_url, filename)
                touch.print(marker_filename)
                if filename.exists() and filename.is_file() and expected_md5:
                    current_md5 = _md5sum(filename)
                    if expected_md5 is not None:
                        if current_md5 != expected_md5:
                            log.debug("Generated md5sum: %s", current_md5)
                            log.debug("Expected md5sum: %s", expected_md5)
                            raise ValueError(
                                ('Generated md5sum does not match expected md5sum '
                                 'for {} recipe').format(self.name))
            else:
                log.info("%s download already cached, skipping", self.name)

    def unpack(self, arch):
        log.info("Unpacking %s for %s", self.name, arch)
        build_dir = self.get_build_container_dir(arch)
        user_dir = os.environ.get(f"P4A_{self.name.lower()}_DIR")
        if user_dir is not None:
            log.info("P4A_%s_DIR exists, symlinking instead", self.name.lower())
            if self.get_build_dir(arch).exists():
                return
            rm._rf.print(build_dir)
            mkdir._p.print(build_dir)
            rmdir.print(build_dir)
            build_dir.mkdirp()
            cp._a.print(user_dir, self.get_build_dir(arch))
            return
        if self.url is None:
            log.info("Skipping %s unpack as no URL is set", self.name)
            return
        # TODO: Parse the URL instead.
        filename = basename(self.versioned_url)[:-1]
        ma = re.match('^(.+)#md5=([0-9a-f]{32})$', filename)
        if ma:                  # fragmented URL?
            filename = ma.group(1)
        with current_directory(build_dir):
            directory_name = self.get_build_dir(arch)
            if not directory_name.exists() or not directory_name.is_dir():
                extraction_filename = self.ctx.packages_path / self.name / filename
                if extraction_filename.is_file():
                    if extraction_filename.name.endswith('.zip'):
                        try:
                            unzip.print(extraction_filename)
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
                            mv.print(root_directory, directory_name)
                    elif extraction_filename.name.endswith(('.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz')):
                        tar.xf.print(extraction_filename)
                        root_directory = tar.tf(extraction_filename).split('\n')[0].split('/')[0]
                        if root_directory != directory_name.name:
                            mv.print(root_directory, directory_name)
                    else:
                        raise Exception(f"Could not extract {extraction_filename} download, it must be .zip, .tar.gz or .tar.bz2 or .tar.xz")
                elif extraction_filename.is_dir():
                    directory_name.mkdir()
                    for entry in extraction_filename.iterdir():
                        if entry.name not in {'.git'}:
                            cp._Rv.print(entry, directory_name)
                else:
                    raise Exception(f"Given path is neither a file nor a directory: {extraction_filename}")
            else:
                log.info("%s is already unpacked, skipping", self.name)

    def get_recipe_env(self, arch=None, with_flags_in_cc=True):
        """Return the env specialized for the recipe
        """
        if arch is None:
            arch = self.filtered_archs[0]
        env = arch.get_env(with_flags_in_cc=with_flags_in_cc)

        if self.need_stl_shared:
            env['CPPFLAGS'] = env.get('CPPFLAGS', '')
            env['CPPFLAGS'] += ' -I{}'.format(self.stl_include_dir)

            env['CXXFLAGS'] = env['CFLAGS'] + ' -frtti -fexceptions'

            if with_flags_in_cc:
                env['CXX'] += ' -frtti -fexceptions'

            env['LDFLAGS'] += ' -L{}'.format(self.get_stl_lib_dir(arch))
            env['LIBS'] = env.get('LIBS', '') + " -l{}".format(
                self.stl_lib_name
            )
        return env

    def prebuild_arch(self, arch):
        '''Run any pre-build tasks for the Recipe. By default, this checks if
        any prebuild_archname methods exist for the archname of the current
        architecture, and runs them if so.'''
        prebuild = "prebuild_{}".format(arch.arch.replace('-', '_'))
        if hasattr(self, prebuild):
            getattr(self, prebuild)()
        else:
            log.info("%s has no %s, skipping", self.name, prebuild)

    def is_patched(self, arch):
        build_dir = self.get_build_dir(arch.arch)
        return (build_dir / '.patched').exists()

    def apply_patches(self, arch, build_dir=None):
        '''Apply any patches for the Recipe.

        .. versionchanged:: 0.6.0
            Add ability to apply patches from any dir via kwarg `build_dir`'''
        if self.patches:
            log.info("Applying patches for %s[%s]", self.name, arch.arch)
            if self.is_patched(arch):
                log.info("%s already patched, skipping", self.name)
                return
            build_dir = build_dir if build_dir else self.get_build_dir(arch.arch)
            for patch in self.patches:
                if isinstance(patch, (tuple, list)):
                    patch, patch_check = patch
                    if not patch_check(arch=arch, recipe=self):
                        continue

                self.apply_patch(
                        patch.format(version=self.version, arch=arch.arch),
                        arch.arch, build_dir=build_dir)
            touch.print(join(build_dir, '.patched'))

    def should_build(self, arch):
        return not all(lib.exists() for lib in self.get_libraries(arch.arch)) if self.built_libraries else True

    def build_arch(self, arch):
        '''Run any build tasks for the Recipe. By default, this checks if
        any build_archname methods exist for the archname of the current
        architecture, and runs them if so.'''
        build = "build_{}".format(arch.arch)
        if hasattr(self, build):
            getattr(self, build)()

    def install_libraries(self, arch):
        '''This method is always called after `build_arch`. In case that we
        detect a library recipe, defined by the class attribute
        `built_libraries`, we will copy all defined libraries into the
         right location.
        '''
        if not self.built_libraries:
            return
        shared_libs = [lib for lib in self.get_libraries(arch) if str(lib).endswith(".so")]
        self.install_libs(arch, *shared_libs)

    def postbuild_arch(self, arch):
        '''Run any post-build tasks for the Recipe. By default, this checks if
        any postbuild_archname methods exist for the archname of the
        current architecture, and runs them if so.
        '''
        postbuild = "postbuild_{}".format(arch.arch)
        if hasattr(self, postbuild):
            getattr(self, postbuild)()

        if self.need_stl_shared:
            self.install_stl_lib(arch)

    def prepare_build_dir(self, arch):
        '''Copies the recipe data into a build dir for the given arch. By
        default, this unpacks a downloaded recipe. You should override
        it (or use a Recipe subclass with different behaviour) if you
        want to do something else.
        '''
        self.unpack(arch)

    def install_libs(self, arch, *libs):
        libs_dir = self.ctx.get_libs_dir(arch.arch)
        if not libs:
            log.warning('install_libs called with no libraries to install!')
            return
        args = libs + (libs_dir,)
        cp.print(*args)

    def has_libs(self, arch, *libs):
        return all(map(lambda l: self.ctx.has_lib(arch.arch, l), libs))

    def get_libraries(self, arch_name, in_context=False):
        """Return the full path of the library depending on the architecture.
        Per default, the build library path it will be returned, unless
        `get_libraries` has been called with kwarg `in_context` set to
        True.

        .. note:: this method should be used for library recipes only
        """
        recipe_libs = set()
        if not self.built_libraries:
            return recipe_libs
        for lib, rel_path in self.built_libraries.items():
            if not in_context:
                abs_path = self.get_build_dir(arch_name) / rel_path / lib
                if rel_path in {".", "", None}:
                    abs_path = self.get_build_dir(arch_name) / lib
            else:
                abs_path = self.ctx.get_libs_dir(arch_name) / lib
            recipe_libs.add(abs_path)
        return recipe_libs

    def get_recipe(self, name):
        return self.ctx.get_recipe(name)

class IncludedFilesBehaviour:

    def prepare_build_dir(self, arch):
        rm._rf.print(self.get_build_dir(arch))
        cp._a.print(self.get_recipe_dir() / self.src_filename, self.get_build_dir(arch))

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

    def get_recipe_env(self, arch=None, with_flags_in_cc=True, with_python=False):
        env = super().get_recipe_env(arch, with_flags_in_cc)
        if not with_python:
            return env
        env['PYTHON_INCLUDE_ROOT'] = self.ctx.python_recipe.include_root(arch.arch)
        env['PYTHON_LINK_ROOT'] = self.ctx.python_recipe.link_root(arch.arch)
        env['EXTRA_LDLIBS'] = ' -lpython{}'.format(
            self.ctx.python_recipe.major_minor_version_string)
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
        return self.get_build_dir(arch.arch) / 'obj' / 'local' / arch.arch

    def get_jni_dir(self, arch):
        return self.get_build_dir(arch.arch) / 'jni'

    def build_arch(self, arch, *extra_args):
        super().build_arch(arch)
        Program.text(self.ctx.ndk_dir / 'ndk-build').print('V=1', f"APP_PLATFORM=android-{self.ctx.ndk_api}", f"APP_ABI={arch.arch}", *extra_args,
                env = self.get_recipe_env(arch), cwd = self.get_build_dir(arch.arch))

class PythonRecipe(Recipe):
    site_packages_name = None
    '''The name of the module's folder when installed in the Python
    site-packages (e.g. for pyjnius it is 'jnius')'''

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

    def get_recipe_env(self, arch=None, with_flags_in_cc=True):
        env = super().get_recipe_env(arch, with_flags_in_cc)
        env['PYTHONNOUSERSITE'] = '1'

        # Set the LANG, this isn't usually important but is a better default
        # as it occasionally matters how Python e.g. reads files
        env['LANG'] = "en_GB.UTF-8"

        if not self.call_hostpython_via_targetpython:
            python_name = self.ctx.python_recipe.name
            env['CFLAGS'] += ' -I{}'.format(
                self.ctx.python_recipe.include_root(arch.arch)
            )
            env['LDFLAGS'] += ' -L{} -lpython{}'.format(
                self.ctx.python_recipe.link_root(arch.arch),
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
        name = self.site_packages_name
        if name is None:
            name = self.name
        if self.ctx.has_package(name):
            log.info('Python package already exists in site-packages')
            return False
        log.info("%s apparently isn't already in site-packages", name)
        return True

    def build_arch(self, arch):
        '''Install the Python module by calling setup.py install with
        the target Python dir.'''
        super().build_arch(arch)
        self.install_python_package(arch)

    def install_python_package(self, arch, name=None, env=None, is_dir=True):
        '''Automate the installation of a Python package (or a cython
        package where the cython components are pre-built).'''
        # arch = self.filtered_archs[0]  # old kivy-ios way
        if name is None:
            name = self.name
        if env is None:
            env = self.get_recipe_env(arch)
        log.info("Installing %s into site-packages", self.name)
        builddir = self.get_build_dir(arch.arch)
        hostpython = Program.text(self.hostpython_location)
        hpenv = env.copy()
        hostpython.print('setup.py', 'install', '-O2', f"--root={self.ctx.get_python_install_dir()}", '--install-lib=.', *self.setup_extra_args, env = hpenv, cwd = builddir)
        if self.install_in_hostpython:
            with current_directory(builddir):
                self.install_hostpython_package(arch)

    def get_hostrecipe_env(self, arch):
        env = os.environ.copy()
        env['PYTHONPATH'] = self.real_hostpython_location.parent / 'Lib' / 'site-packages'
        return env

    def install_hostpython_package(self, arch):
        env = self.get_hostrecipe_env(arch)
        real_hostpython = Program.text(self.real_hostpython_location)
        real_hostpython.print('setup.py', 'install', '-O2', f"--root={self.real_hostpython_location.parent}", '--install-lib=Lib/site-packages', *self.setup_extra_args, env = env)

class CompiledComponentsPythonRecipe(PythonRecipe):

    pre_build_ext = False
    build_cmd = 'build_ext'

    def build_arch(self, arch):
        Recipe.build_arch(self, arch)
        self.build_compiled_components(arch)
        self.install_python_package(arch)

    def build_compiled_components(self, arch):
        log.info("Building compiled components in %s", self.name)
        env = self.get_recipe_env(arch)
        builddir = self.get_build_dir(arch.arch)
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
        hostpython = Program.text(self.real_hostpython_location)
        hostpython.print('setup.py', 'clean', '--all', env = env)
        hostpython.print('setup.py', self.build_cmd, '-v', *self.setup_extra_args, env = env)

class CppCompiledComponentsPythonRecipe(CompiledComponentsPythonRecipe):
    """ Extensions that require the cxx-stl """
    call_hostpython_via_targetpython = False
    need_stl_shared = True


class CythonRecipe(PythonRecipe):
    pre_build_ext = False
    cythonize = True
    cython_args = []
    call_hostpython_via_targetpython = False

    def build_arch(self, arch):
        '''Build any cython components, then install the Python module by
        calling setup.py install with the target Python dir.
        '''
        Recipe.build_arch(self, arch)
        self.build_cython_components(arch)
        self.install_python_package(arch)

    def build_cython_components(self, arch):
        log.info("Cythonizing anything necessary in %s", self.name)
        env = self.get_recipe_env(arch)
        builddir = self.get_build_dir(arch.arch)
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
        self.strip_object_files(arch, env, builddir)

    def strip_object_files(self, arch, env, build_dir):
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

    def get_recipe_env(self, arch, with_flags_in_cc=True):
        env = super().get_recipe_env(arch, with_flags_in_cc)
        env['LDFLAGS'] += f" -L{self.ctx.get_libs_dir(arch.arch)} -L{self.ctx.libs_dir}  -L{self.ctx.bootstrap.build_dir / 'obj' / 'local' / arch.arch} "
        env['LDSHARED'] = env['CC'] + ' -shared'
        env['LIBLINK'] = 'NOTNONE'
        env['NDKPLATFORM'] = self.ctx.ndk_platform
        env['COPYLIBS'] = '1'
        env['LIBLINK_PATH'] = str((self.get_build_container_dir(arch.arch) / f"objects_{self.name}").mkdirp())
        return env

class TargetPythonRecipe(Recipe):

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        self.ctx.python_recipe = self # XXX: Can this suck less?

    def include_root(self, arch):
        '''The root directory from which to include headers.'''
        raise NotImplementedError('Not implemented in TargetPythonRecipe')

    def link_root(self):
        raise NotImplementedError('Not implemented in TargetPythonRecipe')

    @property
    def major_minor_version_string(self):
        return '.'.join(str(v) for v in LooseVersion(self.version).version[:2])

    def reduce_object_file_names(self, dirn):
        """Recursively renames all files named YYY.cpython-...-linux-gnu.so"
        to "YYY.so", i.e. removing the erroneous architecture name
        coming from the local system.
        """
        for filen in find(dirn, '-iname', '*.so').splitlines():
            file_dirname, file_basename = split(filen)
            parts = file_basename.split('.')
            if len(parts) > 2:
                mv.print(filen, join(file_dirname, parts[0] + '.so'))

def _md5sum(filen):
    with open(filen, 'rb') as fileh:
        return hashlib.md5(fileh.read()).hexdigest()
