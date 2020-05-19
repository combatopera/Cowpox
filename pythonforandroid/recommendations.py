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

from .logger import info, warning
from .util import BuildInterruptingException
from distutils.version import LooseVersion

# We only check the NDK major version
MIN_NDK_VERSION = 19
MAX_NDK_VERSION = 20

# DO NOT CHANGE LINE FORMAT: buildozer parses the existence of a RECOMMENDED_NDK_VERSION
RECOMMENDED_NDK_VERSION = "19b"

NDK_DOWNLOAD_URL = "https://developer.android.com/ndk/downloads/"

# Important log messages
NEW_NDK_MESSAGE = 'Newer NDKs may not be fully supported by p4a.'
UNKNOWN_NDK_MESSAGE = (
    'Could not determine NDK version, no source.properties in the NDK dir.'
)
PARSE_ERROR_NDK_MESSAGE = (
    'Could not parse $NDK_DIR/source.properties, not checking NDK version.'
)
READ_ERROR_NDK_MESSAGE = (
    'Unable to read the NDK version from the given directory {ndk_dir}.'
)
ENSURE_RIGHT_NDK_MESSAGE = (
    'Make sure your NDK version is greater than {min_supported}. If you get '
    'build errors, download the recommended NDK {rec_version} from {ndk_url}.'
)
NDK_LOWER_THAN_SUPPORTED_MESSAGE = (
    'The minimum supported NDK version is {min_supported}. '
    'You can download it from {ndk_url}.'
)
UNSUPPORTED_NDK_API_FOR_ARMEABI_MESSAGE = (
    'Asked to build for armeabi architecture with API '
    '{req_ndk_api}, but API {max_ndk_api} or greater does not support armeabi.'
)
CURRENT_NDK_VERSION_MESSAGE = (
    'Found NDK version {ndk_version}'
)
RECOMMENDED_NDK_VERSION_MESSAGE = (
    'Maximum recommended NDK version is {recommended_ndk_version}, but newer versions may work.'
)

def check_ndk_version(ndk_dir):
    version = _read_ndk_version(ndk_dir)
    if version is None:
        warning(READ_ERROR_NDK_MESSAGE.format(ndk_dir=ndk_dir))
        warning(
            ENSURE_RIGHT_NDK_MESSAGE.format(
                min_supported=MIN_NDK_VERSION,
                rec_version=RECOMMENDED_NDK_VERSION,
                ndk_url=NDK_DOWNLOAD_URL,
            )
        )
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

    info(CURRENT_NDK_VERSION_MESSAGE.format(ndk_version=string_version))

    if major_version < MIN_NDK_VERSION:
        raise BuildInterruptingException(
            NDK_LOWER_THAN_SUPPORTED_MESSAGE.format(
                min_supported=MIN_NDK_VERSION, ndk_url=NDK_DOWNLOAD_URL
            ),
            instructions=(
                'Please, go to the android NDK page ({ndk_url}) and download a'
                ' supported version.\n*** The currently recommended NDK'
                ' version is {rec_version} ***'.format(
                    ndk_url=NDK_DOWNLOAD_URL,
                    rec_version=RECOMMENDED_NDK_VERSION,
                )
            ),
        )
    elif major_version > MAX_NDK_VERSION:
        warning(
            RECOMMENDED_NDK_VERSION_MESSAGE.format(
                recommended_ndk_version=RECOMMENDED_NDK_VERSION
            )
        )
        warning(NEW_NDK_MESSAGE)

def _read_ndk_version(ndk_dir):
    try:
        ndk_data = (ndk_dir / 'source.properties').read_text()
    except IOError:
        info(UNKNOWN_NDK_MESSAGE)
        return
    for line in ndk_data.split('\n'):
        if line.startswith('Pkg.Revision'):
            break
    else:
        info(PARSE_ERROR_NDK_MESSAGE)
        return
    ndk_version = LooseVersion(line.split('=')[-1].strip())
    return ndk_version

MIN_TARGET_API = 26
ARMEABI_MAX_TARGET_API = 21
OLD_API_MESSAGE = (
    'Target APIs lower than 26 are no longer supported on Google Play, '
    'and are not recommended. Note that the Target API can be higher than '
    'your device Android version, and should usually be as high as possible.')


def check_target_api(api, arch):
    """Warn if the user's target API is less than the current minimum
    recommendation
    """

    if api >= ARMEABI_MAX_TARGET_API and arch == 'armeabi':
        raise BuildInterruptingException(
            UNSUPPORTED_NDK_API_FOR_ARMEABI_MESSAGE.format(
                req_ndk_api=api, max_ndk_api=ARMEABI_MAX_TARGET_API
            ),
            instructions='You probably want to build with --arch=armeabi-v7a instead')

    if api < MIN_TARGET_API:
        warning('Target API {} < {}'.format(api, MIN_TARGET_API))
        warning(OLD_API_MESSAGE)

MIN_NDK_API = 21
OLD_NDK_API_MESSAGE = ('NDK API less than {} is not supported'.format(MIN_NDK_API))
TARGET_NDK_API_GREATER_THAN_TARGET_API_MESSAGE = (
    'Target NDK API is {ndk_api}, '
    'higher than the target Android API {android_api}.'
)

def check_ndk_api(ndk_api, android_api):
    if ndk_api > android_api:
        raise BuildInterruptingException(
                TARGET_NDK_API_GREATER_THAN_TARGET_API_MESSAGE.format(ndk_api = ndk_api, android_api = android_api),
                instructions = 'The NDK API is a minimum supported API number and must be lower than the target Android API')
    if ndk_api < MIN_NDK_API:
        warning(OLD_NDK_API_MESSAGE)
