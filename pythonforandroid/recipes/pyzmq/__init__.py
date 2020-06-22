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

# coding=utf-8

from pythonforandroid.recipe import CythonRecipe, Recipe
from os.path import join
from pythonforandroid.util import current_directory
import sh
from pythonforandroid.logger import shprint
import glob


class PyZMQRecipe(CythonRecipe):
    name = 'pyzmq'
    version = 'master'
    url = 'https://github.com/zeromq/pyzmq/archive/{version}.zip'
    site_packages_name = 'zmq'
    depends = ['libzmq']
    cython_args = ['-Izmq/utils',
                   '-Izmq/backend/cython',
                   '-Izmq/devices']

    def get_recipe_env(self, arch=None):
        env = super(PyZMQRecipe, self).get_recipe_env(arch)
        # TODO: fix hardcoded path
        # This is required to prevent issue with _io.so import.
        # hostpython = self.get_recipe('hostpython2', self.ctx)
        # env['PYTHONPATH'] = (
        #     join(hostpython.get_build_dir(arch.arch), 'build',
        #          'lib.linux-x86_64-2.7') + ':' + env.get('PYTHONPATH', '')
        # )
        # env["LDSHARED"] = env["CC"] + ' -shared'
        return env

    def build_cython_components(self, arch):
        libzmq_recipe = Recipe.get_recipe('libzmq', self.ctx)
        libzmq_prefix = join(libzmq_recipe.get_build_dir(arch.arch), "install")
        self.setup_extra_args = ["--zmq={}".format(libzmq_prefix)]
        self.build_cmd = "configure"

        env = self.get_recipe_env(arch)
        setup_cfg = join(self.get_build_dir(arch.arch), "setup.cfg")
        with open(setup_cfg, "wb") as fd:
            fd.write("""
[global]
zmq_prefix = {}
skip_check_zmq = True
""".format(libzmq_prefix).encode())

        return super(PyZMQRecipe, self).build_cython_components(arch)

        with current_directory(self.get_build_dir(arch.arch)):
            hostpython = sh.Command(self.hostpython_location)
            shprint(hostpython, 'setup.py', 'configure', '-v', _env=env)
            shprint(hostpython, 'setup.py', 'build_ext', '-v', _env=env)
            build_dir = glob.glob('build/lib.*')[0]
            shprint(sh.find, build_dir, '-name', '"*.o"', '-exec',
                    env['STRIP'], '{}', ';', _env=env)


recipe = PyZMQRecipe()
