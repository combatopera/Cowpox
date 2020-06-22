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

from pythonforandroid.recipe import PythonRecipe
from pythonforandroid.toolchain import current_directory, shprint
import sh


class Psycopg2Recipe(PythonRecipe):
    """
    Requires `libpq-dev` system dependency e.g. for `pg_config` binary.
    If you get `nl_langinfo` symbol runtime error, make sure you're running on
    `ANDROID_API` (`ndk-api`) >= 26, see:
    https://github.com/kivy/python-for-android/issues/1711#issuecomment-465747557
    """
    version = '2.8.4'
    url = 'https://pypi.python.org/packages/source/p/psycopg2/psycopg2-{version}.tar.gz'
    depends = ['libpq']
    site_packages_name = 'psycopg2'
    call_hostpython_via_targetpython = False

    def prebuild_arch(self, arch):
        libdir = self.ctx.get_libs_dir(arch.arch)
        with current_directory(self.get_build_dir(arch.arch)):
            # pg_config_helper will return the system installed libpq, but we
            # need the one we just cross-compiled
            shprint(sh.sed, '-i',
                    "s|pg_config_helper.query(.libdir.)|'{}'|".format(libdir),
                    'setup.py')

    def get_recipe_env(self, arch):
        env = super(Psycopg2Recipe, self).get_recipe_env(arch)
        env['LDFLAGS'] = "{} -L{}".format(env['LDFLAGS'], self.ctx.get_libs_dir(arch.arch))
        env['EXTRA_CFLAGS'] = "--host linux-armv"
        return env

    def install_python_package(self, arch, name=None, env=None, is_dir=True):
        '''Automate the installation of a Python package (or a cython
        package where the cython components are pre-built).'''
        if env is None:
            env = self.get_recipe_env(arch)

        with current_directory(self.get_build_dir(arch.arch)):
            hostpython = sh.Command(self.ctx.hostpython)

            shprint(hostpython, 'setup.py', 'build_ext', '--static-libpq',
                    _env=env)
            shprint(hostpython, 'setup.py', 'install', '-O2',
                    '--root={}'.format(self.ctx.get_python_install_dir()),
                    '--install-lib=.', _env=env)


recipe = Psycopg2Recipe()
