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

from lagoon import cp, virtualenv
from lagoon.program import Program
from os.path import join, dirname, exists, split, isdir
from pathlib import Path
from pythonforandroid.archs import ArchARM, ArchARMv7_a, ArchAarch_64, Archx86, Archx86_64
from pythonforandroid.pythonpackage import get_package_name
from pythonforandroid.recipe import CythonRecipe, Recipe
from pythonforandroid.recommendations import check_ndk_version, check_target_api, check_ndk_api
from pythonforandroid.util import current_directory, ensure_dir, BuildInterruptingException
import copy, glob, logging, os, re, sh, subprocess

log = logging.getLogger(__name__)

def get_ndk_platform_dir(ndk_dir, ndk_api, arch):
    ndk_platform_dir_exists = True
    platform_dir = arch.platform_dir
    ndk_platform = ndk_dir / 'platforms' / f"android-{ndk_api}" / platform_dir
    if not ndk_platform.exists():
        log.warning("ndk_platform doesn't exist: %s", ndk_platform)
        ndk_platform_dir_exists = False
    return ndk_platform, ndk_platform_dir_exists

def get_toolchain_versions(ndk_dir, arch):
    toolchain_versions = []
    toolchain_path_exists = True
    toolchain_prefix = arch.toolchain_prefix
    toolchain_path = join(ndk_dir, 'toolchains')
    if isdir(toolchain_path):
        toolchain_contents = glob.glob('{}/{}-*'.format(toolchain_path,
                                                        toolchain_prefix))
        toolchain_versions = [split(path)[-1][len(toolchain_prefix) + 1:]
                              for path in toolchain_contents]
    else:
        log.warning('Could not find toolchain subdirectory!')
        toolchain_path_exists = False
    return toolchain_versions, toolchain_path_exists


def get_targets(sdk_dir):
    if exists(join(sdk_dir, 'tools', 'bin', 'avdmanager')):
        avdmanager = sh.Command(join(sdk_dir, 'tools', 'bin', 'avdmanager'))
        targets = avdmanager('list', 'target').stdout.decode('utf-8').split('\n')
    elif exists(join(sdk_dir, 'tools', 'android')):
        android = sh.Command(join(sdk_dir, 'tools', 'android'))
        targets = android('list').stdout.decode('utf-8').split('\n')
    else:
        raise BuildInterruptingException(
            'Could not find `android` or `sdkmanager` binaries in Android SDK',
            instructions='Make sure the path to the Android SDK is correct')
    return targets


def _apilevels(sdk_dir):
    targets = get_targets(sdk_dir)
    apis = [s for s in targets if re.match(r'^ *API level: ', s)]
    apis = [re.findall(r'[0-9]+', s) for s in apis]
    return [int(s[0]) for s in apis if s]

class Context:

    env = os.environ.copy()
    # the filepath of toolchain.py
    distribution = None
    libs_dir = None
    aars_dir = None
    ccache = None  # whether to use ccache

    ndk_platform = None  # the ndk platform directory

    bootstrap = None
    bootstrap_build_dir = None

    recipe_build_order = None  # Will hold the list of all built recipes

    @property
    def packages_path(self):
        return self.storage_dir / 'packages'

    @property
    def libs_dir(self):
        dir = self.buildsdir / 'libs_collections' / self.bootstrap.distribution.name
        ensure_dir(dir)
        return dir

    @property
    def javaclass_dir(self):
        dir = self.buildsdir / 'javaclasses' / self.bootstrap.distribution.name
        ensure_dir(dir)
        return dir

    @property
    def aars_dir(self):
        dir = self.buildsdir / 'aars' / self.bootstrap.distribution.name
        ensure_dir(dir)
        return dir

    @property
    def python_installs_dir(self):
        dir = self.buildsdir / 'python-installs'
        ensure_dir(dir)
        return dir

    def get_python_install_dir(self):
        dir = join(self.python_installs_dir, self.bootstrap.distribution.name)
        return dir

    def setup_dirs(self, storage_dir):
        self.buildsdir = storage_dir / 'build'
        self.distsdir = storage_dir / 'dists'
        self.storage_dir = storage_dir

    def ensure_dirs(self):
        ensure_dir(self.storage_dir)
        ensure_dir(self.buildsdir)
        ensure_dir(self.distsdir)
        ensure_dir(self.buildsdir / 'bootstrap_builds')
        ensure_dir(self.buildsdir / 'other_builds')

    def prepare_build_environment(self, user_ndk_api, sdkpath, apilevel, ndkpath):
        self.ensure_dirs()
        self.sdk_dir = sdkpath
        self.android_api = apilevel
        log.info("Found Android API target in $ANDROIDAPI: %s", apilevel)
        check_target_api(apilevel, self.archs[0].arch)
        apis = _apilevels(sdkpath)
        log.info("Available Android APIs are (%s)", ', '.join(map(str, apis)))
        if apilevel not in apis:
            raise BuildInterruptingException("Requested API target %s is not available, install it with the SDK android tool." % apilevel)
        log.info("Requested API target %s is available, continuing.", apilevel)
        self.ndk_dir = ndkpath
        log.info("Found NDK dir in $ANDROIDNDK: %s", ndkpath)
        check_ndk_version(ndkpath)
        log.info('Getting NDK API version (i.e. minimum supported API) from user argument')
        check_ndk_api(user_ndk_api, apilevel)
        self.ndk_api = user_ndk_api
        self.ccache = sh.which("ccache")
        if not self.ccache:
            log.info('ccache is missing, the build will not be optimized in the future.')
        try:
            subprocess.check_call(['python3', '-m', 'cython', '--help'])
        except subprocess.CalledProcessError:
            log.warning('Cython for python3 missing. If you are building for  a python 3 target (which is the default) then THINGS WILL BREAK.')
        arch = self.archs[0]
        toolchain_prefix = arch.toolchain_prefix
        self.ndk_platform, ndk_platform_dir_exists = get_ndk_platform_dir(ndkpath, self.ndk_api, arch)
        toolchain_versions, toolchain_path_exists = get_toolchain_versions(ndkpath, arch)
        toolchain_versions.sort()
        toolchain_versions_gcc = [tv for tv in toolchain_versions if tv[0].isdigit()]
        if toolchain_versions:
            log.info("Found the following toolchain versions: %s", toolchain_versions)
            log.info("Picking the latest gcc toolchain, here %s", toolchain_versions_gcc[-1])
            toolchain_version = toolchain_versions_gcc[-1]
            ok = ndk_platform_dir_exists and toolchain_path_exists
        else:
            log.warning("Could not find any toolchain for %s!", toolchain_prefix)
            ok = False
        if not ok:
            raise BuildInterruptingException('python-for-android cannot continue due to the missing executables above')
        self.toolchain_prefix = toolchain_prefix
        self.toolchain_version = toolchain_version

    def __init__(self):
        self.include_dirs = []
        self.ndk = None

        self.toolchain_prefix = None
        self.toolchain_version = None
        self.archs = (
            ArchARM(self),
            ArchARMv7_a(self),
            Archx86(self),
            Archx86_64(self),
            ArchAarch_64(self),
        )
        self.root_dir = (Path(__file__).parent.parent / 'pythonforandroid').resolve()
        self.env.pop("LDFLAGS", None)
        self.env.pop("ARCHFLAGS", None)
        self.env.pop("CFLAGS", None)

        self.python_recipe = None  # Set by TargetPythonRecipe

    def set_archs(self, arch_names):
        all_archs = self.archs
        new_archs = set()
        for name in arch_names:
            matching = [arch for arch in all_archs if arch.arch == name]
            for match in matching:
                new_archs.add(match)
        self.archs = list(new_archs)
        if not self.archs:
            raise BuildInterruptingException('Asked to compile for no Archs, so failing.')
        log.info("Will compile for the following archs: %s", ', '.join(arch.arch for arch in self.archs))

    def prepare_bootstrap(self, bs):
        bs.ctx = self
        self.bootstrap = bs
        self.bootstrap.prepare_build_dir()
        self.bootstrap_build_dir = self.bootstrap.build_dir

    def prepare_dist(self):
        self.bootstrap.prepare_dist_dir()

    def get_site_packages_dir(self, arch=None):
        '''Returns the location of site-packages in the python-install build
        dir.
        '''
        return self.get_python_install_dir()

    def get_libs_dir(self, arch):
        '''The libs dir for a given arch.'''
        ensure_dir(join(self.libs_dir, arch))
        return join(self.libs_dir, arch)

    def has_lib(self, arch, lib):
        return exists(join(self.get_libs_dir(arch), lib))

    def has_package(self, name, arch=None):
        # If this is a file path, it'll need special handling:
        if (name.find("/") >= 0 or name.find("\\") >= 0) and \
                name.find("://") < 0:  # (:// would indicate an url)
            if not os.path.exists(name):
                # Non-existing dir, cannot look this up.
                return False
            try:
                name = get_package_name(os.path.abspath(name))
            except ValueError:
                # Failed to look up any meaningful name.
                return False

        # Try to look up recipe by name:
        try:
            recipe = Recipe.get_recipe(name, self)
        except ValueError:
            pass
        else:
            name = getattr(recipe, 'site_packages_name', None) or name
        name = name.replace('.', '/')
        site_packages_dir = self.get_site_packages_dir(arch)
        return (exists(join(site_packages_dir, name)) or
                exists(join(site_packages_dir, name + '.py')) or
                exists(join(site_packages_dir, name + '.pyc')) or
                exists(join(site_packages_dir, name + '.pyo')) or
                exists(join(site_packages_dir, name + '.so')) or
                glob.glob(join(site_packages_dir, name + '-*.egg')))

    def not_has_package(self, name, arch=None):
        return not self.has_package(name, arch)

def build_recipes(build_order, python_modules, ctx):
    # Put recipes in correct build order
    log.info("Recipe build order is %s", build_order)
    if python_modules:
        python_modules = sorted(set(python_modules))
        log.info("The requirements (%s) were not found as recipes, they will be installed with pip.", ', '.join(python_modules))
    recipes = [Recipe.get_recipe(name, ctx) for name in build_order]
    # download is arch independent
    log.info('Downloading recipes')
    for recipe in recipes:
        recipe.download_if_necessary()
    for arch in ctx.archs:
        log.info("Building all recipes for arch %s", arch.arch)
        log.info('Unpacking recipes')
        for recipe in recipes:
            ensure_dir(recipe.get_build_container_dir(arch.arch))
            recipe.prepare_build_dir(arch.arch)
        log.info('Prebuilding recipes')
        # 2) prebuild packages
        for recipe in recipes:
            log.info("Prebuilding %s for %s", recipe.name, arch.arch)
            recipe.prebuild_arch(arch)
            recipe.apply_patches(arch)
        # 3) build packages
        log.info('Building recipes')
        for recipe in recipes:
            log.info("Building {} for {}", recipe.name, arch.arch)
            if recipe.should_build(arch):
                recipe.build_arch(arch)
                recipe.install_libraries(arch)
            else:
                log.info("%s said it is already built, skipping", recipe.name)
        # 4) biglink everything
        log.info('Biglinking object files')
        if not ctx.python_recipe:
            biglink(ctx, arch)
        else:
            log.warning('''Context's python recipe found, skipping biglink (will this work?)''')
        # 5) postbuild packages
        log.info('Postbuilding recipes')
        for recipe in recipes:
            log.info("Postbuilding %s for %s", recipe.name, arch.arch)
            recipe.postbuild_arch(arch)
    log.info('Installing pure Python modules')
    log.info('*** PYTHON PACKAGE / PROJECT INSTALL STAGE ***')
    modules = list(filter(ctx.not_has_package, python_modules))
    if not modules:
        log.info('No Python modules and no setup.py to process, skipping')
        return
    log.info("The requirements (%s) don't have recipes, attempting to install them with pip", ', '.join(modules))
    log.info('If this fails, it may mean that the module has compiled components and needs a recipe.')
    with current_directory(ctx.buildsdir):
        virtualenv.print(f"--python=python{ctx.python_recipe.major_minor_version_string.partition('.')[0]}", 'venv')
        base_env = os.environ.copy()
        base_env["PYTHONPATH"] = ctx.get_site_packages_dir()
        log.info('Upgrade pip to latest version')
        pip = Program.text(Path('venv', 'bin', 'pip'))
        pip.install._U.print('pip', env = base_env)
        log.info('Install Cython in case one of the modules needs it to build')
        pip.install.print('Cython', env = base_env)
        # Get environment variables for build (with CC/compiler set):
        standard_recipe = CythonRecipe()
        standard_recipe.ctx = ctx
        # (note: following line enables explicit -lpython... linker options)
        standard_recipe.call_hostpython_via_targetpython = False
        recipe_env = standard_recipe.get_recipe_env(ctx.archs[0])
        env = copy.copy(base_env)
        env.update(recipe_env)

        # Make sure our build package dir is available, and the virtualenv
        # site packages come FIRST (so the proper pip version is used):
        env["PYTHONPATH"] += ":" + ctx.get_site_packages_dir()
        env["PYTHONPATH"] = os.path.abspath(ctx.buildsdir / 'venv' / 'lib' / f"python{ctx.python_recipe.major_minor_version_string}" / 'site-packages') + ":" + env["PYTHONPATH"]
        # Install the manually specified requirements first:
        if not modules:
            log.info('There are no Python modules to install, skipping')
        else:
            log.info('Creating a requirements.txt file for the Python modules')
            with open('requirements.txt', 'w') as fileh:
                for module in modules:
                    key = 'VERSION_' + module
                    if key in os.environ:
                        line = '{}=={}\n'.format(module, os.environ[key])
                    else:
                        line = '{}\n'.format(module)
                    fileh.write(line)
            log.info('Installing Python modules with pip')
            log.info('IF THIS FAILS, THE MODULES MAY NEED A RECIPE. A reason for this is often modules compiling native code that is unaware of Android cross-compilation and does not work without additional changes / workarounds.')
            pip.install._v.__no_deps.print('--target', ctx.get_site_packages_dir(), '-r', 'requirements.txt', '-f', '/wheels', env = env)
        standard_recipe.strip_object_files(ctx.archs[0], env, build_dir = ctx.buildsdir)

def biglink(ctx, arch):
    log.info('Collating object files from each recipe')
    obj_dir = join(ctx.bootstrap.build_dir, 'collated_objects')
    ensure_dir(obj_dir)
    recipes = [Recipe.get_recipe(name, ctx) for name in ctx.recipe_build_order]
    for recipe in recipes:
        recipe_obj_dir = join(recipe.get_build_container_dir(arch.arch),
                              'objects_{}'.format(recipe.name))
        if not exists(recipe_obj_dir):
            log.info("%s recipe has no biglinkable files dir, skipping", recipe.name)
            continue
        files = glob.glob(join(recipe_obj_dir, '*'))
        if not len(files):
            log.info("%s recipe has no biglinkable files, skipping", recipe.name)
            continue
        log.info("%s recipe has object files, copying", recipe.name)
        files.append(obj_dir)
        cp._r.print(*files)
    env = arch.get_env()
    env['LDFLAGS'] = env['LDFLAGS'] + ' -L{}'.format(
        join(ctx.bootstrap.build_dir, 'obj', 'local', arch.arch))
    if not len(glob.glob(join(obj_dir, '*'))):
        log.info('There seem to be no libraries to biglink, skipping.')
        return
    log.info('Biglinking')
    log.info("target %s", join(ctx.get_libs_dir(arch.arch), 'libpymodules.so'))
    # Move to the directory containing crtstart_so.o and crtend_so.o
    # This is necessary with newer NDKs? A gcc bug?
    with current_directory(join(ctx.ndk_platform, 'usr', 'lib')):
        copylibs_function(
            join(ctx.get_libs_dir(arch.arch), 'libpymodules.so'),
            obj_dir.split(' '),
            extra_link_dirs=[join(ctx.bootstrap.build_dir,
                                  'obj', 'local', arch.arch),
                             os.path.abspath('.')],
            env=env)

def copylibs_function(soname, objs_paths, extra_link_dirs=[], env=None):
    print('objs_paths are', objs_paths)

    re_needso = re.compile(r'^.*\(NEEDED\)\s+Shared library: \[lib(.*)\.so\]\s*$')
    blacklist_libs = (
        'c',
        'stdc++',
        'dl',
        'python2.7',
        'sdl',
        'sdl_image',
        'sdl_ttf',
        'z',
        'm',
        'GLESv2',
        'jpeg',
        'png',
        'log',

        # bootstrap takes care of sdl2 libs (if applicable)
        'SDL2',
        'SDL2_ttf',
        'SDL2_image',
        'SDL2_mixer',
    )
    found_libs = []
    sofiles = []
    if env and 'READELF' in env:
        readelf = env['READELF']
    elif 'READELF' in os.environ:
        readelf = os.environ['READELF']
    else:
        readelf = sh.which('readelf').strip()
    readelf = sh.Command(readelf).bake('-d')

    dest = dirname(soname)

    for directory in objs_paths:
        for fn in os.listdir(directory):
            fn = join(directory, fn)

            if not fn.endswith('.libs'):
                continue

            dirfn = fn[:-1] + 'dirs'
            if not exists(dirfn):
                continue

            with open(fn) as f:
                libs = f.read().strip().split(' ')
                needed_libs = [lib for lib in libs
                               if lib and
                               lib not in blacklist_libs and
                               lib not in found_libs]

            while needed_libs:
                print('need libs:\n\t' + '\n\t'.join(needed_libs))

                start_needed_libs = needed_libs[:]
                found_sofiles = []

                with open(dirfn) as f:
                    libdirs = f.read().split()
                    for libdir in libdirs:
                        if not needed_libs:
                            break

                        if libdir == dest:
                            # don't need to copy from dest to dest!
                            continue

                        libdir = libdir.strip()
                        print('scanning', libdir)
                        for lib in needed_libs[:]:
                            if lib in found_libs:
                                continue

                            if lib.endswith('.a'):
                                needed_libs.remove(lib)
                                found_libs.append(lib)
                                continue

                            lib_a = 'lib' + lib + '.a'
                            libpath_a = join(libdir, lib_a)
                            lib_so = 'lib' + lib + '.so'
                            libpath_so = join(libdir, lib_so)
                            plain_so = lib + '.so'
                            plainpath_so = join(libdir, plain_so)

                            sopath = None
                            if exists(libpath_so):
                                sopath = libpath_so
                            elif exists(plainpath_so):
                                sopath = plainpath_so

                            if sopath:
                                print('found', lib, 'in', libdir)
                                found_sofiles.append(sopath)
                                needed_libs.remove(lib)
                                found_libs.append(lib)
                                continue

                            if exists(libpath_a):
                                print('found', lib, '(static) in', libdir)
                                needed_libs.remove(lib)
                                found_libs.append(lib)
                                continue

                for sofile in found_sofiles:
                    print('scanning dependencies for', sofile)
                    out = readelf(sofile)
                    for line in out.splitlines():
                        needso = re_needso.match(line)
                        if needso:
                            lib = needso.group(1)
                            if (lib not in needed_libs
                                    and lib not in found_libs
                                    and lib not in blacklist_libs):
                                needed_libs.append(needso.group(1))

                sofiles += found_sofiles

                if needed_libs == start_needed_libs:
                    raise RuntimeError(
                            'Failed to locate needed libraries!\n\t' +
                            '\n\t'.join(needed_libs))
    print('Copying libraries')
    for lib in sofiles:
        cp.print(lib, dest)
