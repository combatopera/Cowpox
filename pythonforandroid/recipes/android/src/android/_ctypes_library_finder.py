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


import os


def get_activity_lib_dir(activity_name):
    from jnius import autoclass

    # Get the actual activity instance:
    activity_class = autoclass(activity_name)
    if activity_class is None:
        return None
    activity = None
    if hasattr(activity_class, "mActivity") and \
            activity_class.mActivity is not None:
        activity = activity_class.mActivity
    elif hasattr(activity_class, "mService") and \
            activity_class.mService is not None:
        activity = activity_class.mService
    if activity is None:
        return None

    # Extract the native lib dir from the activity instance:
    package_name = activity.getApplicationContext().getPackageName()
    manager = activity.getApplicationContext().getPackageManager()
    manager_class = autoclass("android.content.pm.PackageManager")
    native_lib_dir = manager.getApplicationInfo(
        package_name, manager_class.GET_SHARED_LIBRARY_FILES
    ).nativeLibraryDir
    return native_lib_dir


def does_libname_match_filename(search_name, file_path):
    # Filter file names so given search_name="mymodule" we match one of:
    #      mymodule.so         (direct name + .so)
    #      libmymodule.so      (added lib prefix)
    #      mymodule.arm64.so   (added dot-separated middle parts)
    #      mymodule.so.1.3.4   (added dot-separated version tail)
    #      and all above       (all possible combinations)
    import re
    file_name = os.path.basename(file_path)
    return (re.match(r"^(lib)?" + re.escape(search_name) +
                     r"\.(.*\.)?so(\.[0-9]+)*$", file_name) is not None)


def find_library(name):
    # Obtain all places for native libraries:
    lib_search_dirs = ["/system/lib"]
    lib_dir_1 = get_activity_lib_dir("org.kivy.android.PythonActivity")
    if lib_dir_1 is not None:
        lib_search_dirs.insert(0, lib_dir_1)
    lib_dir_2 = get_activity_lib_dir("org.kivy.android.PythonService")
    if lib_dir_2 is not None and lib_dir_2 not in lib_search_dirs:
        lib_search_dirs.insert(0, lib_dir_2)

    # Now scan the lib dirs:
    for lib_dir in [l for l in lib_search_dirs if os.path.exists(l)]:
        filelist = [
            f for f in os.listdir(lib_dir)
            if does_libname_match_filename(name, f)
        ]
        if len(filelist) > 0:
            return os.path.join(lib_dir, filelist[0])
    return None
