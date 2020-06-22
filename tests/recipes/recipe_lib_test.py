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

from unittest import mock
from platform import system
from tests.recipes.recipe_ctx import RecipeCtx


class BaseTestForMakeRecipe(RecipeCtx):
    """
    An unittest for testing any recipe using the standard build commands
    (`configure/make`).

    .. note:: Note that Some cmake recipe may need some more specific testing
        ...but this should cover the basics.
    """

    recipe_name = None
    expected_compiler = (
        "{android_ndk}/toolchains/llvm/prebuilt/{system}-x86_64/bin/clang"
    )

    sh_command_calls = ["./configure"]
    """The expected commands that the recipe runs via `sh.command`."""

    extra_env_flags = {}
    """
    This must be a dictionary containing pairs of key (env var) and value.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.recipes = ["python3", "kivy", self.recipe_name]
        self.recipe_build_order = [
            "hostpython3", self.recipe_name, "python3", "sdl2", "kivy"
        ]
        print(f"We are testing recipe: {self.recipe_name}")

    @mock.patch("pythonforandroid.recipe.Recipe.check_recipe_choices")
    @mock.patch("pythonforandroid.build.ensure_dir")
    @mock.patch("pythonforandroid.archs.glob")
    @mock.patch("pythonforandroid.archs.find_executable")
    def test_get_recipe_env(
        self,
        mock_find_executable,
        mock_glob,
        mock_ensure_dir,
        mock_check_recipe_choices,
    ):
        """
        Test that get_recipe_env contains some expected arch flags and that
        some internal methods has been called.
        """
        mock_find_executable.return_value = self.expected_compiler.format(
                android_ndk=self.ctx._ndk_dir, system=system().lower()
        )
        mock_glob.return_value = ["llvm"]
        mock_check_recipe_choices.return_value = sorted(
            self.ctx.recipe_build_order
        )

        # make sure the arch flags are in env
        env = self.recipe.get_recipe_env(self.arch)
        for flag in self.arch.arch_cflags:
            self.assertIn(flag, env["CFLAGS"])
        self.assertIn(
            f"-target {self.arch.target}",
            env["CFLAGS"],
        )

        for flag, value in self.extra_env_flags.items():
            self.assertIn(value, env[flag])

        # make sure that the mocked methods are actually called
        mock_glob.assert_called()
        mock_ensure_dir.assert_called()
        mock_find_executable.assert_called()
        mock_check_recipe_choices.assert_called()

    @mock.patch("pythonforandroid.util.chdir")
    @mock.patch("pythonforandroid.build.ensure_dir")
    @mock.patch("pythonforandroid.archs.glob")
    @mock.patch("pythonforandroid.archs.find_executable")
    def test_build_arch(
        self,
        mock_find_executable,
        mock_glob,
        mock_ensure_dir,
        mock_current_directory,
    ):
        mock_find_executable.return_value = self.expected_compiler.format(
                android_ndk=self.ctx._ndk_dir, system=system().lower()
        )
        mock_glob.return_value = ["llvm"]

        # Since the following mocks are dynamic,
        # we mock it inside a Context Manager
        with mock.patch(
            f"pythonforandroid.recipes.{self.recipe_name}.sh.Command"
        ) as mock_sh_command, mock.patch(
            f"pythonforandroid.recipes.{self.recipe_name}.sh.make"
        ) as mock_make:
            self.recipe.build_arch(self.arch)

        # make sure that the mocked methods are actually called
        for command in self.sh_command_calls:
            self.assertIn(
                mock.call(command),
                mock_sh_command.mock_calls,
            )
        mock_make.assert_called()
        mock_glob.assert_called()
        mock_ensure_dir.assert_called()
        mock_current_directory.assert_called()
        mock_find_executable.assert_called()


class BaseTestForCmakeRecipe(BaseTestForMakeRecipe):
    """
    An unittest for testing any recipe using `cmake`. It inherits from
    `BaseTestForMakeRecipe` but we override the build method to match the cmake
    build method.

    .. note:: Note that Some cmake recipe may need some more specific testing
        ...but this should cover the basics.
    """

    @mock.patch("pythonforandroid.util.chdir")
    @mock.patch("pythonforandroid.build.ensure_dir")
    @mock.patch("pythonforandroid.archs.glob")
    @mock.patch("pythonforandroid.archs.find_executable")
    def test_build_arch(
        self,
        mock_find_executable,
        mock_glob,
        mock_ensure_dir,
        mock_current_directory,
    ):
        mock_find_executable.return_value = self.expected_compiler.format(
                android_ndk=self.ctx._ndk_dir, system=system().lower()
        )
        mock_glob.return_value = ["llvm"]

        # Since the following mocks are dynamic,
        # we mock it inside a Context Manager
        with mock.patch(
            f"pythonforandroid.recipes.{self.recipe_name}.sh.make"
        ) as mock_make, mock.patch(
            f"pythonforandroid.recipes.{self.recipe_name}.sh.cmake"
        ) as mock_cmake:
            self.recipe.build_arch(self.arch)

        # make sure that the mocked methods are actually called
        mock_cmake.assert_called()
        mock_make.assert_called()
        mock_glob.assert_called()
        mock_ensure_dir.assert_called()
        mock_current_directory.assert_called()
        mock_find_executable.assert_called()
