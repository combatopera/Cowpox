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

# Downloads and installs the Android SDK depending on supplied platform: darwin or linux

# We must provide a platform (darwin or linux) and we need JAVA_HOME defined
ifndef target_os
    $(error target_os is not set...aborted!)
endif

# Those android NDK/SDK variables can be override when running the file
ANDROID_NDK_VERSION ?= 19b
ANDROID_SDK_TOOLS_VERSION ?= 4333796
ANDROID_SDK_BUILD_TOOLS_VERSION ?= 28.0.2
ANDROID_HOME ?= $(HOME)/.android
ANDROID_API_LEVEL ?= 27

ANDROID_SDK_HOME=$(ANDROID_HOME)/android-sdk
ANDROID_SDK_TOOLS_ARCHIVE=sdk-tools-$(target_os)-$(ANDROID_SDK_TOOLS_VERSION).zip
ANDROID_SDK_TOOLS_DL_URL=https://dl.google.com/android/repository/$(ANDROID_SDK_TOOLS_ARCHIVE)

ANDROID_NDK_HOME=$(ANDROID_HOME)/android-ndk
ANDROID_NDK_FOLDER=$(ANDROID_HOME)/android-ndk-r$(ANDROID_NDK_VERSION)
ANDROID_NDK_ARCHIVE=android-ndk-r$(ANDROID_NDK_VERSION)-$(target_os)-x86_64.zip
ANDROID_NDK_DL_URL=https://dl.google.com/android/repository/$(ANDROID_NDK_ARCHIVE)

$(info Target install OS is          : $(target_os))
$(info Android SDK home is           : $(ANDROID_SDK_HOME))
$(info Android NDK home is           : $(ANDROID_NDK_HOME))
$(info Android SDK download url is   : $(ANDROID_SDK_TOOLS_DL_URL))
$(info Android NDK download url is   : $(ANDROID_NDK_DL_URL))
$(info Android API level is          : $(ANDROID_API_LEVEL))
$(info Android NDK version is        : $(ANDROID_NDK_VERSION))
$(info JAVA_HOME is                  : $(JAVA_HOME))

all: install_sdk install_ndk

install_sdk: download_android_sdk extract_android_sdk update_android_sdk

install_ndk: download_android_ndk extract_android_ndk

download_android_sdk:
	curl --location --progress-bar --continue-at - \
	$(ANDROID_SDK_TOOLS_DL_URL) --output $(ANDROID_SDK_TOOLS_ARCHIVE)

download_android_ndk:
	curl --location --progress-bar --continue-at - \
	$(ANDROID_NDK_DL_URL) --output $(ANDROID_NDK_ARCHIVE)

# Extract android SDK and remove the compressed file
extract_android_sdk:
	mkdir -p $(ANDROID_SDK_HOME) \
	&& unzip -q $(ANDROID_SDK_TOOLS_ARCHIVE) -d $(ANDROID_SDK_HOME) \
	&& rm -f $(ANDROID_SDK_TOOLS_ARCHIVE)


# Extract android NDK and remove the compressed file
extract_android_ndk:
	mkdir -p $(ANDROID_NDK_FOLDER) \
	&& unzip -q $(ANDROID_NDK_ARCHIVE) -d $(ANDROID_HOME) \
	&& ln -sfn $(ANDROID_NDK_FOLDER) $(ANDROID_NDK_HOME) \
	&& rm -f $(ANDROID_NDK_ARCHIVE)

# updates Android SDK, install Android API, Build Tools and accept licenses
update_android_sdk:
	touch $(ANDROID_HOME)/repositories.cfg
	yes | $(ANDROID_SDK_HOME)/tools/bin/sdkmanager --licenses > /dev/null
	$(ANDROID_SDK_HOME)/tools/bin/sdkmanager "build-tools;$(ANDROID_SDK_BUILD_TOOLS_VERSION)" > /dev/null
	$(ANDROID_SDK_HOME)/tools/bin/sdkmanager "platforms;android-$(ANDROID_API_LEVEL)" > /dev/null
	# Set avdmanager permissions (executable)
	chmod +x $(ANDROID_SDK_HOME)/tools/bin/avdmanager
