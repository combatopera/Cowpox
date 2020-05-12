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

from sys import exit
import os

class Target:

    def __init__(self, buildozer):
        self.buildozer = buildozer
        self.build_mode = 'debug'
        self.platform_update = False

    def check_requirements(self):
        pass

    def compile_platform(self):
        pass

    def install_platform(self):
        pass

    def get_available_packages(self):
        return ['kivy']

    def run_commands(self, args):
        if not args:
            self.buildozer.error('Missing target command')
            exit(1)

        result = []
        last_command = []
        while args:
            arg = args.pop(0)
            if arg == '--':
                if last_command:
                    last_command += args
                    break
            elif not arg.startswith('--'):
                if last_command:
                    result.append(last_command)
                    last_command = []
                last_command.append(arg)
            else:
                if not last_command:
                    self.buildozer.error('Argument passed without a command')
                    exit(1)
                last_command.append(arg)
        if last_command:
            result.append(last_command)
        for item in result:
            command, args = item[0], item[1:]
            getattr(self, f"cmd_{command}")(args)

    def cmd_clean(self, *args):
        self.buildozer.clean_platform()

    def cmd_update(self, *args):
        self.platform_update = True
        self.buildozer.prepare_for_build()

    def cmd_debug(self, *args):
        self.buildozer.prepare_for_build()
        self.build_mode = 'debug'
        self.buildozer.build()

    def cmd_release(self, *args):
        error = self.buildozer.error
        self.buildozer.prepare_for_build()
        if self.buildozer.config.get("app", "package.domain") == "org.test":
            error("")
            error("ERROR: Trying to release a package that starts with org.test")
            error("")
            error("The package.domain org.test is, as the name intented, a test.")
            error("Once you published an application with org.test,")
            error("you cannot change it, it will be part of the identifier")
            error("for Google Play / App Store / etc.")
            error("")
            error("So change package.domain to anything else.")
            error("")
            error("If you messed up before, set the environment variable to force the build:")
            error("export BUILDOZER_ALLOW_ORG_TEST_DOMAIN=1")
            error("")
            if "BUILDOZER_ALLOW_ORG_TEST_DOMAIN" not in os.environ:
                exit(1)

        if self.buildozer.config.get("app", "package.domain") == "org.kivy":
            error("")
            error("ERROR: Trying to release a package that starts with org.kivy")
            error("")
            error("The package.domain org.kivy is reserved for the Kivy official")
            error("applications. Please use your own domain.")
            error("")
            error("If you are a Kivy developer, add an export in your shell")
            error("export BUILDOZER_ALLOW_KIVY_ORG_DOMAIN=1")
            error("")
            if "BUILDOZER_ALLOW_KIVY_ORG_DOMAIN" not in os.environ:
                exit(1)

        self.build_mode = 'release'
        self.buildozer.build()
