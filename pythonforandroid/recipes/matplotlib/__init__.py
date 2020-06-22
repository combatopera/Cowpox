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

from os.path import join
from p4a import CppCompiledComponentsPythonRecipe
from pathlib import Path
import logging

log = logging.getLogger(__name__)

class MatplotlibRecipe(CppCompiledComponentsPythonRecipe):

    version = '3.1.3'
    url = 'https://github.com/matplotlib/matplotlib/archive/v{version}.zip'

    depends = ['numpy', 'png', 'setuptools', 'freetype', 'kiwisolver']
    conflicts = ['python2']

    python_depends = ['pyparsing', 'cycler', 'python-dateutil']

    # We need to patch to:
    # - make mpl install work without importing numpy
    # - make mpl use shared libraries for freetype and png
    # - make mpl link to png16, to match p4a library name for png
    # - prevent mpl trying to build TkAgg, which wouldn't work
    #   on Android anyway but has build issues
    patches = ['mpl_android_fixes.patch']

    call_hostpython_via_targetpython = False

    def generate_libraries_pc_files(self, arch):
        """
        Create *.pc files for libraries that `matplotib` depends on.

        Because, for unix platforms, the mpl install script uses `pkg-config`
        to detect libraries installed in non standard locations (our case...
        well...we don't even install the libraries...so we must trick a little
        the mlp install).
        """
        pkg_config_path = Path(self.get_recipe_env(arch)['PKG_CONFIG_PATH']).mkdirp()
        lib_to_pc_file = {
            # `pkg-config` search for version freetype2.pc, our current
            # version for freetype, but we have our recipe named without
            # the version...so we add it in here for our pc file
            'freetype': 'freetype2.pc',
            'png': 'png.pc',
        }

        for lib_name in {'freetype', 'png'}:
            pc_template_file = join(
                self.get_recipe_dir(),
                f'lib{lib_name}.pc.template'
            )
            # read template file into buffer
            with open(pc_template_file) as template_file:
                text_buffer = template_file.read()
            # set the library absolute path and library version
            lib_recipe = self.get_recipe(lib_name)
            text_buffer = text_buffer.replace('path_to_built', lib_recipe.get_build_dir(arch.arch))
            text_buffer = text_buffer.replace('library_version', lib_recipe.version)
            (pkg_config_path / lib_to_pc_file[lib_name]).write_text(text_buffer)

    def download_web_backend_dependencies(self, arch):
        """
        During building, host needs to download the jquery-ui package (in order
        to make it work the mpl web backend). This operation seems to fail
        in our CI tests, so we download this package at the expected location
        by the mpl install script which is defined by the environ variable
        `XDG_CACHE_HOME` (we modify that one in our `get_recipe_env` so it will
        be the same regardless of the host platform).
        """

        env = self.get_recipe_env(arch)
        log.info('Downloading jquery-ui for matplatlib web backend')
        # We use the same jquery-ui version than mpl's setup.py script,
        # inside function `_download_jquery_to`
        jquery_sha = (
            'f8233674366ab36b2c34c577ec77a3d70cac75d2e387d8587f3836345c0f624d'
        )
        url = 'https://jqueryui.com/resources/download/jquery-ui-1.12.1.zip'
        log.info("Will download into %s", env['XDG_CACHE_HOME'])
        matplotlibdir = Path(env['XDG_CACHE_HOME'], 'matplotlib').mkdirp()
        self.download_file(url, matplotlibdir / jquery_sha)

    def prebuild_arch(self, arch):
        with open(join(self.get_recipe_dir(), 'setup.cfg.template')) as fileh:
            setup_cfg = fileh.read()

        with open(join(self.get_build_dir(arch), 'setup.cfg'), 'w') as fileh:
            fileh.write(setup_cfg.format(
                ndk_sysroot_usr=join(self.ctx.ndk_dir, 'sysroot', 'usr')))

        self.generate_libraries_pc_files(arch)
        self.download_web_backend_dependencies(arch)

    def get_recipe_env(self, arch=None, with_flags_in_cc=True):
        env = super().get_recipe_env(arch, with_flags_in_cc)
        if self.need_stl_shared:
            # matplotlib compile flags does not honor the standard flags:
            # `CPPFLAGS` and `LDLIBS`, so we put in `CFLAGS` and `LDFLAGS` to
            # correctly link with the `c++_shared` library
            env['CFLAGS'] += ' -I{}'.format(self.stl_include_dir)
            env['CFLAGS'] += ' -frtti -fexceptions'

            env['LDFLAGS'] += ' -L{}'.format(self.get_stl_lib_dir(arch))
            env['LDFLAGS'] += ' -l{}'.format(self.stl_lib_name)

        # we modify `XDG_CACHE_HOME` to download `jquery-ui` into that folder,
        # or mpl install will fail when trying to download/install it, but if
        # we have the proper package already downloaded, it will use the cached
        # package to successfully finish the installation.
        # Note: this may not be necessary for some local systems, but it is
        #       for our CI providers: `gh-actions` and travis, which will
        #       fail trying to download the `jquery-ui` package
        env['XDG_CACHE_HOME'] = join(self.get_build_dir(arch), 'p4a_files')
        # we make use of the same directory than `XDG_CACHE_HOME`, for our
        # custom library pc files, so we have all the install files that we
        # generate at the same place
        env['PKG_CONFIG_PATH'] = env['XDG_CACHE_HOME']

        # We set a new environ variable `NUMPY_INCLUDES` to be able to tell
        # the matplotlib script where to find our numpy without importing it
        # (which will fail, because numpy isn't installed in our hostpython)
        env['NUMPY_INCLUDES'] = join(
            self.ctx.get_site_packages_dir(),
            'numpy', 'core', 'include',
        )

        # creating proper *.pc files for our libraries does not seem enough to
        # success with our build (without depending on system development
        # libraries), but if we tell the compiler where to find our libraries
        # and includes, then the install success :)
        png = self.get_recipe('png')
        env['CFLAGS'] += f' -I{png.get_build_dir(arch)}'
        env['LDFLAGS'] += f' -L{join(png.get_build_dir(arch.arch), ".libs")}'
        freetype = self.get_recipe('freetype')
        free_lib_dir = join(freetype.get_build_dir(arch.arch), 'objs', '.libs')
        free_inc_dir = join(freetype.get_build_dir(arch.arch), 'include')
        env['CFLAGS'] += f' -I{free_inc_dir}'
        env['LDFLAGS'] += f' -L{free_lib_dir}'

        # `freetype` could be built with `harfbuzz` support,
        # so we also include the necessary flags...just to be sure
        if 'harfbuzz' in self.ctx.recipe_build_order:
            harfbuzz = self.get_recipe('harfbuzz')
            harf_build = harfbuzz.get_build_dir(arch.arch)
            env['CFLAGS'] += f' -I{harf_build} -I{join(harf_build, "src")}'
            env['LDFLAGS'] += f' -L{join(harf_build, "src", ".libs")}'
        return env


recipe = MatplotlibRecipe()
