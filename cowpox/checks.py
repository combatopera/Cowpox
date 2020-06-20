from .config import Config
from .platform import Platform
from .recommendations import check_ndk_version, check_target_api, check_ndk_api
from diapyr import types
from p4a import Arch
from pathlib import Path
import logging

log = logging.getLogger(__name__)

class Checks:

    @types(Config, Platform, Arch)
    def __init__(self, config, platform, arch):
        self.ndk_api = config.android.ndk_api
        self.android_api = config.android.api
        self.ndk_dir = Path(config.android_ndk_dir)
        self.platform = platform
        self.arch = arch

    def check(self):
        check_target_api(self.android_api, self.arch.name)
        apis = self.platform.apilevels()
        log.info("Available Android APIs are (%s)", ', '.join(map(str, apis)))
        if self.android_api not in apis:
            raise Exception("Requested API target %s is not available, install it with the SDK android tool." % self.android_api)
        log.info("Requested API target %s is available, continuing.", self.android_api)
        check_ndk_version(self.ndk_dir)
        check_ndk_api(self.ndk_api, self.android_api)
