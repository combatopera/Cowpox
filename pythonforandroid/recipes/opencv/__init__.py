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

from os.path import join
import sh
from pythonforandroid.recipe import NDKRecipe
from pythonforandroid.util import current_directory
from pythonforandroid.logger import shprint
from multiprocessing import cpu_count


class OpenCVRecipe(NDKRecipe):
    '''
    .. versionchanged:: 0.7.1
        rewrote recipe to support the python bindings (cv2.so) and enable the
        build of most of the libraries of the opencv's package, so we can
        process images, videos, objects, photos...
    '''
    version = '4.0.1'
    url = 'https://github.com/opencv/opencv/archive/{version}.zip'
    depends = ['numpy']
    patches = ['patches/p4a_build.patch']
    generated_libraries = [
        'libopencv_features2d.so',
        'libopencv_imgproc.so',
        'libopencv_stitching.so',
        'libopencv_calib3d.so',
        'libopencv_flann.so',
        'libopencv_ml.so',
        'libopencv_videoio.so',
        'libopencv_core.so',
        'libopencv_highgui.so',
        'libopencv_objdetect.so',
        'libopencv_video.so',
        'libopencv_dnn.so',
        'libopencv_imgcodecs.so',
        'libopencv_photo.so'
    ]

    def get_lib_dir(self, arch):
        return join(self.get_build_dir(arch.arch), 'build', 'lib', arch.arch)

    def get_recipe_env(self, arch):
        env = super(OpenCVRecipe, self).get_recipe_env(arch)
        env['ANDROID_NDK'] = self.ctx.ndk_dir
        env['ANDROID_SDK'] = self.ctx.sdk_dir
        return env

    def build_arch(self, arch):
        build_dir = join(self.get_build_dir(arch.arch), 'build')
        shprint(sh.mkdir, '-p', build_dir)
        with current_directory(build_dir):
            env = self.get_recipe_env(arch)

            python_major = self.ctx.python_recipe.version[0]
            python_include_root = self.ctx.python_recipe.include_root(arch.arch)
            python_site_packages = self.ctx.get_site_packages_dir()
            python_link_root = self.ctx.python_recipe.link_root(arch.arch)
            python_link_version = self.ctx.python_recipe.major_minor_version_string
            if 'python3' in self.ctx.python_recipe.name:
                python_link_version += 'm'
            python_library = join(python_link_root,
                                  'libpython{}.so'.format(python_link_version))
            python_include_numpy = join(python_site_packages,
                                        'numpy', 'core', 'include')

            shprint(sh.cmake,
                    '-DP4A=ON',
                    '-DANDROID_ABI={}'.format(arch.arch),
                    '-DANDROID_STANDALONE_TOOLCHAIN={}'.format(self.ctx.ndk_dir),
                    '-DANDROID_NATIVE_API_LEVEL={}'.format(self.ctx.ndk_api),
                    '-DANDROID_EXECUTABLE={}/tools/android'.format(env['ANDROID_SDK']),

                    '-DCMAKE_TOOLCHAIN_FILE={}'.format(
                        join(self.ctx.ndk_dir, 'build', 'cmake',
                             'android.toolchain.cmake')),
                    # Make the linkage with our python library, otherwise we
                    # will get dlopen error when trying to import cv2's module.
                    '-DCMAKE_SHARED_LINKER_FLAGS=-L{path} -lpython{version}'.format(
                        path=python_link_root,
                        version=python_link_version),

                    '-DBUILD_WITH_STANDALONE_TOOLCHAIN=ON',
                    # Force to build as shared libraries the cv2's dependant
                    # libs or we will not be able to link with our python
                    '-DBUILD_SHARED_LIBS=ON',
                    '-DBUILD_STATIC_LIBS=OFF',

                    # Disable some opencv's features
                    '-DBUILD_opencv_java=OFF',
                    '-DBUILD_opencv_java_bindings_generator=OFF',
                    # '-DBUILD_opencv_highgui=OFF',
                    # '-DBUILD_opencv_imgproc=OFF',
                    # '-DBUILD_opencv_flann=OFF',
                    '-DBUILD_TESTS=OFF',
                    '-DBUILD_PERF_TESTS=OFF',
                    '-DENABLE_TESTING=OFF',
                    '-DBUILD_EXAMPLES=OFF',
                    '-DBUILD_ANDROID_EXAMPLES=OFF',

                    # Force to only build our version of python
                    '-DBUILD_OPENCV_PYTHON{major}=ON'.format(major=python_major),
                    '-DBUILD_OPENCV_PYTHON{major}=OFF'.format(
                        major='2' if python_major == '3' else '3'),

                    # Force to install the `cv2.so` library directly into
                    # python's site packages (otherwise the cv2's loader fails
                    # on finding the cv2.so library)
                    '-DOPENCV_SKIP_PYTHON_LOADER=ON',
                    '-DOPENCV_PYTHON{major}_INSTALL_PATH={site_packages}'.format(
                        major=python_major, site_packages=python_site_packages),

                    # Define python's paths for: exe, lib, includes, numpy...
                    '-DPYTHON_DEFAULT_EXECUTABLE={}'.format(self.ctx.hostpython),
                    '-DPYTHON{major}_EXECUTABLE={host_python}'.format(
                        major=python_major, host_python=self.ctx.hostpython),
                    '-DPYTHON{major}_INCLUDE_PATH={include_path}'.format(
                        major=python_major, include_path=python_include_root),
                    '-DPYTHON{major}_LIBRARIES={python_lib}'.format(
                        major=python_major, python_lib=python_library),
                    '-DPYTHON{major}_NUMPY_INCLUDE_DIRS={numpy_include}'.format(
                        major=python_major, numpy_include=python_include_numpy),
                    '-DPYTHON{major}_PACKAGES_PATH={site_packages}'.format(
                        major=python_major, site_packages=python_site_packages),

                    self.get_build_dir(arch.arch),
                    _env=env)
            shprint(sh.make, '-j' + str(cpu_count()), 'opencv_python' + python_major)
            # Install python bindings (cv2.so)
            shprint(sh.cmake, '-DCOMPONENT=python', '-P', './cmake_install.cmake')
            # Copy third party shared libs that we need in our final apk
            sh.cp('-a', sh.glob('./lib/{}/lib*.so'.format(arch.arch)),
                  self.ctx.get_libs_dir(arch.arch))


recipe = OpenCVRecipe()
