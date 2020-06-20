from .config import Config
from .platform import Platform
from diapyr import types
from p4a import Arch
import logging

log = logging.getLogger(__name__)

class Checks:

    ARMEABI_MAX_TARGET_API = 21
    MIN_TARGET_API = 26
    MIN_NDK_API = 21

    @types(Config, Platform, Arch)
    def __init__(self, config, platform, arch):
        self.ndk_api = config.android.ndk_api
        self.android_api = config.android.api
        self.platform = platform
        self.arch = arch

    def check(self):
        if self.android_api >= self.ARMEABI_MAX_TARGET_API and self.arch.name == 'armeabi':
            raise Exception(
                    f"Asked to build for armeabi architecture with API {self.android_api}, but API {self.ARMEABI_MAX_TARGET_API} or greater does not support armeabi.",
                    'You probably want to build with --arch=armeabi-v7a instead')
        if self.android_api < self.MIN_TARGET_API:
            log.warning("Target API %s < %s", self.android_api, self.MIN_TARGET_API)
            log.warning('Target APIs lower than 26 are no longer supported on Google Play, and are not recommended. Note that the Target API can be higher than your device Android version, and should usually be as high as possible.')
        apis = self.platform.apilevels()
        log.info("Available Android APIs are (%s)", ', '.join(map(str, apis)))
        if self.android_api not in apis:
            raise Exception("Requested API target %s is not available, install it with the SDK android tool." % self.android_api)
        log.info("Requested API target %s is available, continuing.", self.android_api)
        check_ndk_version(self.platform)
        if self.ndk_api > self.android_api:
            raise Exception(
                    f"Target NDK API is {self.ndk_api}, higher than the target Android API {self.android_api}.",
                    'The NDK API is a minimum supported API number and must be lower than the target Android API')
        if self.ndk_api < self.MIN_NDK_API:
            log.warning("NDK API less than %s is not supported", self.MIN_NDK_API)

# We only check the NDK major version
MIN_NDK_VERSION = 19
MAX_NDK_VERSION = 20
NDK_DOWNLOAD_URL = "https://developer.android.com/ndk/downloads/"
NDK_LOWER_THAN_SUPPORTED_MESSAGE = (
    'The minimum supported NDK version is {min_supported}. '
    'You can download it from {ndk_url}.'
)

def check_ndk_version(platform):
    version = platform.read_ndk_version()
    if version is None:
        log.warning("Unable to read the NDK version from the given directory %s.", platform.ndk_dir)
        log.warning("Make sure your NDK version is greater than %s. If you get build errors, download the recommended NDK from %s.", MIN_NDK_VERSION, NDK_DOWNLOAD_URL)
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
                ' supported version.'.format(
                    ndk_url=NDK_DOWNLOAD_URL,
                )
            ),
        )
    elif major_version > MAX_NDK_VERSION:
        log.warning('Newer NDKs may not be fully supported by p4a.')
