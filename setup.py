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

from io import open  # for open(..,encoding=...) parameter in python 2
from os import walk
from os.path import join, dirname, sep
from setuptools import setup, find_packages
import glob, re

# NOTE: All package data should also be set in MANIFEST.in

packages = find_packages()
data_files = []



# must be a single statement since buildozer is currently parsing it, refs:
# https://github.com/kivy/buildozer/issues/722
install_reqs = [
    'appdirs', 'colorama>=0.3.3', 'jinja2', 'six',
    'enum34; python_version<"3.4"', 'sh>=1.10; sys_platform!="nt"',
    'pep517<0.7.0"', 'pytoml', 'virtualenv<20', 'diapyr', 'lagoon',
]
# (pep517, pytoml and virtualenv are used by pythonpackage.py)

# By specifying every file manually, package_data will be able to
# include them in binary distributions. Note that we have to add
# everything as a 'pythonforandroid' rule, using '' apparently doesn't
# work.
def recursively_include(directory, patterns):
    for root, subfolders, files in walk(directory):
        for fn in files:
            if not any([glob.fnmatch.fnmatch(fn, pattern) for pattern in patterns]):
                continue
            filename = join(root, fn)
            directory = 'pythonforandroid'
            if directory not in package_data:
                package_data[directory] = []
            package_data[directory].append(join(*filename.split(sep)[1:]))

package_data = {'': ['*.tmpl', '*.patch']}
recursively_include('pythonforandroid/recipes', ['*.patch', '*.pyx', '*.py', '*.c', '*.h', '*.mk', '*.jam'])
recursively_include('pythonforandroid/bootstraps', ['*.properties', '*.xml', '*.java', '*.tmpl', '*.txt', '*.png', '*.mk', '*.c', '*.h', '*.py', '*.sh', '*.jpg', '*.gradle', '.gitkeep', 'gradlew*', '*.jar', "*.patch"])
recursively_include('pythonforandroid/bootstraps/webview', ['*.html'])
recursively_include('pythonforandroid', ['liblink', 'biglink', 'liblink.sh'])

with open(join(dirname(__file__), 'README.md'),
          encoding="utf-8",
          errors="replace",
         ) as fileh:
    long_description = fileh.read()

init_filen = join(dirname(__file__), 'pythonforandroid', '__init__.py')
version = None
try:
    with open(init_filen,
              encoding="utf-8",
              errors="replace"
             ) as fileh:
        lines = fileh.readlines()
except IOError:
    pass
else:
    for line in lines:
        line = line.strip()
        if line.startswith('__version__ = '):
            matches = re.findall(r'["\'].+["\']', line)
            if matches:
                version = matches[0].strip("'").strip('"')
                break
if version is None:
    raise Exception('Error: version could not be loaded from {}'.format(init_filen))

setup(name='python-for-android',
      version=version,
      description='Android APK packager for Python scripts and apps',
      long_description=long_description,
      long_description_content_type='text/markdown',
      author='The Kivy team',
      author_email='kivy-dev@googlegroups.com',
      url='https://github.com/kivy/python-for-android',
      license='MIT',
      install_requires=install_reqs,
      entry_points={
          'console_scripts': [
              'python-for-android = pythonforandroid.entrypoints:main',
              'p4a = pythonforandroid.entrypoints:main',
              ],
          'distutils.commands': [
              'apk = pythonforandroid.bdistapk:BdistAPK',
              ],
          },
      classifiers = [
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: OS Independent',
          'Operating System :: POSIX :: Linux',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: Android',
          'Programming Language :: C',
          'Programming Language :: Python :: 3',
          'Topic :: Software Development',
          'Topic :: Utilities',
          ],
      packages=packages,
      package_data=package_data,
      )
