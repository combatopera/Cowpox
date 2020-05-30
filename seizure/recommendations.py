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
import logging

log = logging.getLogger(__name__)
# We only check the NDK major version
MIN_NDK_VERSION = 19
MAX_NDK_VERSION = 20

# DO NOT CHANGE LINE FORMAT: buildozer parses the existence of a RECOMMENDED_NDK_VERSION
RECOMMENDED_NDK_VERSION = "19b"

NDK_DOWNLOAD_URL = "https://developer.android.com/ndk/downloads/"
NDK_LOWER_THAN_SUPPORTED_MESSAGE = (
    'The minimum supported NDK version is {min_supported}. '
    'You can download it from {ndk_url}.'
)
UNSUPPORTED_NDK_API_FOR_ARMEABI_MESSAGE = (
    'Asked to build for armeabi architecture with API '
    '{req_ndk_api}, but API {max_ndk_api} or greater does not support armeabi.'
)

def check_ndk_version(ndk_dir):
    version = _read_ndk_version(ndk_dir)
    if version is None:
        log.warning("Unable to read the NDK version from the given directory %s.", ndk_dir)
        log.warning("Make sure your NDK version is greater than %s. If you get build errors, download the recommended NDK %s from %s.", MIN_NDK_VERSION, RECOMMENDED_NDK_VERSION, NDK_DOWNLOAD_URL)
        return
    # create a dictionary which will describe the relationship of the android's
    # NDK minor version with the `human readable` letter version, egs:
    # Pkg.Revision = 17.1.4828580 => ndk-17b
    # Pkg.Revision = 17.2.4988734 => ndk-17c
    # Pkg.Revision = 19.0.5232133 => ndk-19 (No letter)
    minor_to_letter = {0: ''}
    minor_to_letter.update(
        {n + 1: chr(i) for n, i in enumerate(range(ord('b'), ord('b') + 25))}
    )

    major_version = version.version[0]
    letter_version = minor_to_letter[version.version[1]]
    string_version = '{major_version}{letter_version}'.format(
        major_version=major_version, letter_version=letter_version
    )
    log.info("Found NDK version %s", string_version)
    if major_version < MIN_NDK_VERSION:
        raise Exception(
            NDK_LOWER_THAN_SUPPORTED_MESSAGE.format(
                min_supported=MIN_NDK_VERSION, ndk_url=NDK_DOWNLOAD_URL
            ),
            (
                'Please, go to the android NDK page ({ndk_url}) and download a'
                ' supported version.\n*** The currently recommended NDK'
                ' version is {rec_version} ***'.format(
                    ndk_url=NDK_DOWNLOAD_URL,
                    rec_version=RECOMMENDED_NDK_VERSION,
                )
            ),
        )
    elif major_version > MAX_NDK_VERSION:
        log.warning("Maximum recommended NDK version is %s, but newer versions may work.", RECOMMENDED_NDK_VERSION)
        log.warning('Newer NDKs may not be fully supported by p4a.')

def _read_ndk_version(ndk_dir):
    try:
        ndk_data = (ndk_dir / 'source.properties').read_text()
    except IOError:
        log.info('Could not determine NDK version, no source.properties in the NDK dir.')
        return
    for line in ndk_data.split('\n'):
        if line.startswith('Pkg.Revision'):
            break
    else:
        log.info('Could not parse $NDK_DIR/source.properties, not checking NDK version.')
        return
    ndk_version = LooseVersion(line.split('=')[-1].strip())
    return ndk_version

MIN_TARGET_API = 26
ARMEABI_MAX_TARGET_API = 21

def check_target_api(api, arch):
    """Warn if the user's target API is less than the current minimum
    recommendation
    """

    if api >= ARMEABI_MAX_TARGET_API and arch == 'armeabi':
        raise Exception(
            UNSUPPORTED_NDK_API_FOR_ARMEABI_MESSAGE.format(
                req_ndk_api=api, max_ndk_api=ARMEABI_MAX_TARGET_API
            ),
            'You probably want to build with --arch=armeabi-v7a instead')

    if api < MIN_TARGET_API:
        log.warning("Target API %s < %s", api, MIN_TARGET_API)
        log.warning('Target APIs lower than 26 are no longer supported on Google Play, and are not recommended. Note that the Target API can be higher than your device Android version, and should usually be as high as possible.')

MIN_NDK_API = 21
TARGET_NDK_API_GREATER_THAN_TARGET_API_MESSAGE = (
    'Target NDK API is {ndk_api}, '
    'higher than the target Android API {android_api}.'
)

def check_ndk_api(ndk_api, android_api):
    if ndk_api > android_api:
        raise Exception(
                TARGET_NDK_API_GREATER_THAN_TARGET_API_MESSAGE.format(ndk_api = ndk_api, android_api = android_api),
                'The NDK API is a minimum supported API number and must be lower than the target Android API')
    if ndk_api < MIN_NDK_API:
        log.warning("NDK API less than %s is not supported", MIN_NDK_API)
