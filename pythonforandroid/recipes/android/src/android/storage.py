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

from jnius import autoclass, cast
import os


Environment = autoclass('android.os.Environment')
File = autoclass('java.io.File')


def _android_has_is_removable_func():
    VERSION = autoclass('android.os.Build$VERSION')
    return (VERSION.SDK_INT >= 24)


def _get_sdcard_path():
    """ Internal function to return getExternalStorageDirectory()
        path. This is internal because it may either return the internal,
        or an external sd card, depending on the device.
        Use primary_external_storage_path()
        or secondary_external_storage_path() instead which try to
        distinguish this properly.
    """
    return (
        Environment.getExternalStorageDirectory().getAbsolutePath()
    )


def _get_activity():
    """
    Retrieves the activity from `PythonActivity` fallback to `PythonService`.
    """
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    activity = PythonActivity.mActivity
    if activity is None:
        # assume we're running from the background service
        PythonService = autoclass('org.kivy.android.PythonService')
        activity = PythonService.mService
    return activity


def app_storage_path():
    """ Locate the built-in device storage used for this app only.

        This storage is APP-SPECIFIC, and not visible to other apps.
        It will be wiped when your app is uninstalled.

        Returns directory path to storage.
    """
    activity = _get_activity()
    currentActivity = cast('android.app.Activity', activity)
    context = cast('android.content.ContextWrapper',
                   currentActivity.getApplicationContext())
    file_p = cast('java.io.File', context.getFilesDir())
    return os.path.normpath(os.path.abspath(
        file_p.getAbsolutePath().replace("/", os.path.sep)))


def primary_external_storage_path():
    """ Locate the built-in device storage that user can see via file browser.
        Often found at: /sdcard/

        This is storage is SHARED, and visible to other apps and the user.
        It will remain untouched when your app is uninstalled.

        Returns directory path to storage.

        WARNING: You need storage permissions to access this storage.
    """
    if _android_has_is_removable_func():
        sdpath = _get_sdcard_path()
        # Apparently this can both return primary (built-in) or
        # secondary (removable) external storage depending on the device,
        # therefore check that we got what we wanted:
        if not Environment.isExternalStorageRemovable(File(sdpath)):
            return sdpath
    if "EXTERNAL_STORAGE" in os.environ:
        return os.environ["EXTERNAL_STORAGE"]
    raise RuntimeError(
        "unexpectedly failed to determine " +
        "primary external storage path"
    )


def secondary_external_storage_path():
    """ Locate the external SD Card storage, which may not be present.
        Often found at: /sdcard/External_SD/

        This storage is SHARED, visible to other apps, and may not be
        be available if the user didn't put in an external SD card.
        It will remain untouched when your app is uninstalled.

        Returns None if not found, otherwise path to storage.

        WARNING: You need storage permissions to access this storage.
                 If it is not writable and presents as empty even with
                 permissions, then the external sd card may not be present.
    """
    if _android_has_is_removable_func:
        # See if getExternalStorageDirectory() returns secondary ext storage:
        sdpath = _get_sdcard_path()
        # Apparently this can both return primary (built-in) or
        # secondary (removable) external storage depending on the device,
        # therefore check that we got what we wanted:
        if Environment.isExternalStorageRemovable(File(sdpath)):
            if os.path.exists(sdpath):
                return sdpath

    # See if we can take a guess based on environment variables:
    p = None
    if "SECONDARY_STORAGE" in os.environ:
        p = os.environ["SECONDARY_STORAGE"]
    elif "EXTERNAL_SDCARD_STORAGE" in os.environ:
        p = os.environ["EXTERNAL_SDCARD_STORAGE"]
    if p is not None and os.path.exists(p):
        return p
    return None
