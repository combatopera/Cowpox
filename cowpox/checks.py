from .config import Config
from .platform import Platform
from diapyr import types
import logging

log = logging.getLogger(__name__)

class Checks:

    MIN_NDK_VERSION = 19
    NDK_DOWNLOAD_URL = 'https://developer.android.com/ndk/downloads/'
    MAX_NDK_VERSION = 20

    @types(Config, Platform)
    def __init__(self, config, platform):
        self.platform = platform

    def check(self):
        version = self.platform.read_ndk_version()
        minor_to_letter = {0: ''}
        minor_to_letter.update([n + 1, chr(i)] for n, i in enumerate(range(ord('b'), ord('b') + 25)))
        major_version = version.version[0]
        letter_version = minor_to_letter[version.version[1]]
        string_version = f"{major_version}{letter_version}"
        log.info("Found NDK version %s", string_version)
        if major_version < self.MIN_NDK_VERSION:
            raise Exception(
                    f"The minimum supported NDK version is {self.MIN_NDK_VERSION}. You can download it from {self.NDK_DOWNLOAD_URL}.",
                    f"Please, go to the android NDK page ({self.NDK_DOWNLOAD_URL}) and download a supported version.")
        if major_version > self.MAX_NDK_VERSION:
            log.warning('Newer NDKs may not be fully supported by p4a.')
