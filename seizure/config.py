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

from argparse import Namespace
from configparser import SafeConfigParser
from diapyr import types
from pythonforandroid.recommendations import RECOMMENDED_NDK_VERSION
import logging, re

log = logging.getLogger(__name__)

class Config(SafeConfigParser):

    targetname = 'android'
    build_mode = 'debug'

    @types(Namespace)
    def __init__(self, config):
        super().__init__(allow_no_value = True)
        self.workspace = config.workspace
        self.optionxform = lambda value: value
        self.getlist = self._get_config_list
        self.getlistvalues = self._get_config_list_values
        self.getdefault = self._get_config_default
        self.getbooldefault = self._get_config_bool
        self.getrawdefault = self._get_config_raw_default
        self.read('buildozer.spec', 'utf-8')
        self.android_ndk_version = self.getdefault('app', 'android.ndk', RECOMMENDED_NDK_VERSION)

    def _get_config_list_values(self, *args, **kwargs):
        kwargs['with_values'] = True
        return self._get_config_list(*args, **kwargs)

    def _get_config_list(self, section, token, default=None, with_values=False):
        l_section = '{}:{}'.format(section, token)
        if self.has_section(l_section):
            values = self.options(l_section)
            if with_values:
                return ['{}={}'.format(key, self.get(l_section, key)) for
                        key in values]
            else:
                return [x.strip() for x in values]

        values = self.getdefault(section, token, '')
        if not values:
            return default
        values = values.split(',')
        if not values:
            return default
        return [x.strip() for x in values]

    def _get_config_default(self, section, token, default=None):
        if not self.has_section(section):
            return default
        if not self.has_option(section, token):
            return default
        return self.get(section, token)

    def _get_config_bool(self, section, token, default=False):
        if not self.has_section(section):
            return default
        if not self.has_option(section, token):
            return default
        return self.getboolean(section, token)

    def _get_config_raw_default(self, section, token, default=None, section_sep="=", split_char=" "):
        l_section = '{}:{}'.format(section, token)
        if self.has_section(l_section):
            return [section_sep.join(item) for item in self.items(l_section)]
        if not self.has_option(section, token):
            return default.split(split_char)
        return self.get(section, token).split(split_char)

    def get_version(self):
        has_version = self.has_option('app', 'version')
        has_regex = self.has_option('app', 'version.regex')
        has_filename = self.has_option('app', 'version.filename')
        # version number specified
        if has_version:
            if has_regex or has_filename:
                raise Exception('version.regex and version.filename conflict with version')
            return self.get('app', 'version')
        # search by regex
        if has_regex or has_filename:
            if has_regex and not has_filename:
                raise Exception('version.filename is missing')
            if has_filename and not has_regex:
                raise Exception('version.regex is missing')
            fn = self.get('app', 'version.filename')
            with open(fn) as fd:
                data = fd.read()
                regex = self.get('app', 'version.regex')
                match = re.search(regex, data)
                if not match:
                    raise Exception(f'Unable to find capture version in {fn}\n (looking for `{regex}`)')
                version = match.groups()[0]
                log.debug('Captured version: %s', version)
                return version
        raise Exception('Missing version or version.regex + version.filename')
