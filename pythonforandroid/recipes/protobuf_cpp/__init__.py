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

from multiprocessing import cpu_count
from pythonforandroid.logger import info, info_notify, shprint
from pythonforandroid.recipe import CppCompiledComponentsPythonRecipe
from pythonforandroid.util import current_directory
from os.path import exists, join
import os, sh, sys

class ProtobufCppRecipe(CppCompiledComponentsPythonRecipe):
    """This is a two-in-one recipe:
      - build labraru `libprotobuf.so`
      - build and install python binding for protobuf_cpp
    """
    name = 'protobuf_cpp'
    version = '3.6.1'
    url = 'https://github.com/google/protobuf/releases/download/v{version}/protobuf-python-{version}.tar.gz'
    call_hostpython_via_targetpython = False
    depends = ['cffi', 'setuptools']
    site_packages_name = 'google/protobuf/pyext'
    setup_extra_args = ['--cpp_implementation']
    built_libraries = {'libprotobuf.so': 'src/.libs'}
    protoc_dir = None

    def prebuild_arch(self, arch):
        super(ProtobufCppRecipe, self).prebuild_arch(arch)

        patch_mark = join(self.get_build_dir(arch.arch), '.protobuf-patched')
        if self.ctx.python_recipe.name == 'python3' and not exists(patch_mark):
            self.apply_patch('fix-python3-compatibility.patch', arch.arch)
            shprint(sh.touch, patch_mark)

        # During building, host needs to transpile .proto files to .py
        # ideally with the same version as protobuf runtime, or with an older one.
        # Because protoc is compiled for target (i.e. Android), we need an other binary
        # which can be run by host.
        # To make it easier, we download prebuild protoc binary adapted to the platform

        info_notify("Downloading protoc compiler for your platform")
        url_prefix = "https://github.com/protocolbuffers/protobuf/releases/download/v{version}".format(version=self.version)
        if sys.platform.startswith('linux'):
            info_notify("GNU/Linux detected")
            filename = "protoc-{version}-linux-x86_64.zip".format(version=self.version)
        elif sys.platform.startswith('darwin'):
            info_notify("Mac OS X detected")
            filename = "protoc-{version}-osx-x86_64.zip".format(version=self.version)
        else:
            info_notify("Your platform is not supported, but recipe can still "
                        "be built if you have a valid protoc (<={version}) in "
                        "your path".format(version=self.version))
            return

        protoc_url = join(url_prefix, filename)
        self.protoc_dir = self.ctx.buildsdir / "tools" / "protoc"
        if (self.protoc_dir / "bin" / "protoc").exists():
            info_notify("protoc found, no download needed")
            return
        try:
            os.makedirs(self.protoc_dir)
        except OSError as e:
            # if dir already exists (errno 17), we ignore the error
            if e.errno != 17:
                raise e
        info_notify("Will download into {dest_dir}".format(dest_dir=self.protoc_dir))
        self.download_file(protoc_url, join(self.protoc_dir, filename))
        with current_directory(self.protoc_dir):
            shprint(sh.unzip, join(self.protoc_dir, filename))

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)

        # Build libproto.so
        with current_directory(self.get_build_dir(arch.arch)):
            build_arch = (
                shprint(sh.gcc, '-dumpmachine')
                .stdout.decode('utf-8')
                .split('\n')[0]
            )

            if not exists('configure'):
                shprint(sh.Command('./autogen.sh'), _env=env)

            shprint(sh.Command('./configure'),
                    '--build={}'.format(build_arch),
                    '--host={}'.format(arch.command_prefix),
                    '--target={}'.format(arch.command_prefix),
                    '--disable-static',
                    '--enable-shared',
                    _env=env)

            with current_directory(join(self.get_build_dir(arch.arch), 'src')):
                shprint(sh.make, 'libprotobuf.la', '-j'+str(cpu_count()), _env=env)

        self.install_python_package(arch)

    def build_compiled_components(self, arch):
        # Build python bindings and _message.so
        env = self.get_recipe_env(arch)
        with current_directory(join(self.get_build_dir(arch.arch), 'python')):
            hostpython = sh.Command(self.hostpython_location)
            shprint(hostpython,
                    'setup.py',
                    'build_ext',
                    _env=env, *self.setup_extra_args)

    def install_python_package(self, arch):
        env = self.get_recipe_env(arch)

        info('Installing {} into site-packages'.format(self.name))

        with current_directory(join(self.get_build_dir(arch.arch), 'python')):
            hostpython = sh.Command(self.hostpython_location)

            hpenv = env.copy()
            shprint(hostpython, 'setup.py', 'install', '-O2',
                    '--root={}'.format(self.ctx.get_python_install_dir()),
                    '--install-lib=.',
                    _env=hpenv, *self.setup_extra_args)

        # Create __init__.py which is missing, see also:
        #   - https://github.com/protocolbuffers/protobuf/issues/1296
        #   - https://stackoverflow.com/questions/13862562/
        #   google-protocol-buffers-not-found-when-trying-to-freeze-python-app
        open(
            join(self.ctx.get_site_packages_dir(), 'google', '__init__.py'),
            'a',
        ).close()

    def get_recipe_env(self, arch):
        env = super(ProtobufCppRecipe, self).get_recipe_env(arch)
        if self.protoc_dir is not None:
            # we need protoc with binary for host platform
            env['PROTOC'] = join(self.protoc_dir, 'bin', 'protoc')
        env['TARGET_OS'] = 'OS_ANDROID_CROSSCOMPILE'
        env['CXXFLAGS'] += ' -std=c++11'
        env['LDFLAGS'] += ' -lm -landroid -llog'
        return env


recipe = ProtobufCppRecipe()
