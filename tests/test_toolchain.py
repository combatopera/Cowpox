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

import io
import sys
import pytest
from unittest import mock
from pythonforandroid.recipe import Recipe
from pythonforandroid.toolchain import ToolchainCL
from pythonforandroid.util import BuildInterruptingException


def patch_sys_argv(argv):
    return mock.patch('sys.argv', argv)


def patch_argparse_print_help():
    return mock.patch('argparse.ArgumentParser.print_help')


def patch_sys_stdout():
    return mock.patch('sys.stdout', new_callable=io.StringIO)


def raises_system_exit():
    return pytest.raises(SystemExit)


class TestToolchainCL:

    def test_help(self):
        """
        Calling with `--help` should print help and exit 0.
        """
        argv = ['toolchain.py', '--help', '--storage-dir=/tmp']
        with patch_sys_argv(argv), raises_system_exit(
                ) as ex_info, patch_argparse_print_help() as m_print_help:
            ToolchainCL()
        assert ex_info.value.code == 0
        assert m_print_help.call_args_list == [mock.call()]

    @pytest.mark.skipif(sys.version_info < (3, 0), reason="requires python3")
    def test_unknown(self):
        """
        Calling with unknown args should print help and exit 1.
        """
        argv = ['toolchain.py', '--unknown']
        with patch_sys_argv(argv), raises_system_exit(
        ) as ex_info, patch_argparse_print_help() as m_print_help:
            ToolchainCL()
        assert ex_info.value.code == 1
        assert m_print_help.call_args_list == [mock.call()]

    def test_create(self):
        """
        Basic `create` distribution test.
        """
        argv = [
            'toolchain.py',
            'create',
            '--sdk-dir=/tmp/android-sdk',
            '--ndk-dir=/tmp/android-ndk',
            '--bootstrap=service_only',
            '--requirements=python3',
            '--dist-name=test_toolchain',
        ]
        with patch_sys_argv(argv), mock.patch(
            'pythonforandroid.build.get_available_apis'
        ) as m_get_available_apis, mock.patch(
            'pythonforandroid.build.get_toolchain_versions'
        ) as m_get_toolchain_versions, mock.patch(
            'pythonforandroid.build.get_ndk_platform_dir'
        ) as m_get_ndk_platform_dir, mock.patch(
            'pythonforandroid.toolchain.build_recipes'
        ) as m_build_recipes, mock.patch(
            'pythonforandroid.bootstraps.service_only.'
            'ServiceOnlyBootstrap.run_distribute'
        ) as m_run_distribute:
            m_get_available_apis.return_value = [27]
            m_get_toolchain_versions.return_value = (['4.9'], True)
            m_get_ndk_platform_dir.return_value = (
                '/tmp/android-ndk/platforms/android-21/arch-arm', True)
            ToolchainCL()
        assert m_get_available_apis.call_args_list in [
            [mock.call('/tmp/android-sdk')],  # linux case
            [mock.call('/private/tmp/android-sdk')]  # macos case
        ]
        assert m_get_toolchain_versions.call_args_list in [
            [mock.call('/tmp/android-ndk', mock.ANY)],  # linux case
            [mock.call('/private/tmp/android-ndk', mock.ANY)],  # macos case
        ]
        build_order = [
            'hostpython3', 'libffi', 'openssl', 'sqlite3', 'python3',
            'genericndkbuild', 'setuptools', 'six', 'pyjnius', 'android',
        ]
        python_modules = []
        context = mock.ANY
        project_dir = None
        assert m_build_recipes.call_args_list == [
            mock.call(
                build_order,
                python_modules,
                context,
                project_dir,
                ignore_project_setup_py=False
            )
        ]
        assert m_run_distribute.call_args_list == [mock.call()]

    @mock.patch(
        'pythonforandroid.build.environ',
        # Make sure that no environ variable modifies `sdk_dir`
        {'ANDROIDSDK': None, 'ANDROID_HOME': None})
    def test_create_no_sdk_dir(self):
        """
        The `--sdk-dir` is mandatory to `create` a distribution.
        """
        argv = ['toolchain.py', 'create']
        with patch_sys_argv(argv), pytest.raises(
            BuildInterruptingException
        ) as ex_info:
            ToolchainCL()
        assert ex_info.value.message == (
            'Android SDK dir was not specified, exiting.')

    @pytest.mark.skipif(sys.version_info < (3, 0), reason="requires python3")
    def test_recipes(self):
        """
        Checks the `recipes` command prints out recipes information without crashing.
        """
        argv = ['toolchain.py', 'recipes']
        with patch_sys_argv(argv), patch_sys_stdout() as m_stdout:
            ToolchainCL()
        # check if we have common patterns in the output
        expected_strings = (
            'conflicts:',
            'depends:',
            'kivy',
            'optional depends:',
            'python3',
            'sdl2',
        )
        for expected_string in expected_strings:
            assert expected_string in m_stdout.getvalue()
        # deletes static attribute to not mess with other tests
        del Recipe.recipes
