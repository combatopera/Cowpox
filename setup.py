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

from pathlib import Path
from setuptools import find_packages, setup
import glob, re

def find_version(*file_paths):
    here = Path(__file__).parent.resolve()
    # Open in Latin-1 so that we avoid encoding errors.
    with Path(here, *file_paths).open(encoding = 'utf-8') as f:
        version_file = f.read()
    # The version line must have the form
    # __version__ = 'ver'
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

def recursively_include(directory, patterns):
    root = Path('pythonforandroid')
    for path in Path(root, *directory).rglob('*'):
        if any(glob.fnmatch.fnmatch(path.name, pattern) for pattern in patterns):
            package_data[str(root)].append(str(path.relative_to(root)))

package_data = {
        'buildozer': ['default.spec'],
        '': ['*.aridt', '*.tmpl', '*.patch'],
        'pythonforandroid': []}
recursively_include(['recipes'], ['*.patch', '*.pyx', '*.py', '*.c', '*.h', '*.mk', '*.jam'])
recursively_include(['bootstraps'], ['*.properties', '*.xml', '*.java', '*.tmpl', '*.txt', '*.png', '*.mk', '*.c', '*.h', '*.py', '*.sh', '*.jpg', '*.gradle', '.gitkeep', 'gradlew*', '*.jar', '*.patch'])
recursively_include(['bootstraps', 'webview'], ['*.html'])
recursively_include(['tools'], ['liblink', 'biglink', 'liblink.sh'])
projectroot = Path(__file__).parent
with (projectroot / 'README.md').open(encoding = 'utf-8') as f:
    readme = f.read()
with (projectroot / 'CHANGELOG.md').open(encoding = 'utf-8') as f:
    changelog = f.read()
setup(
    name='buildozer',
    version=find_version('buildozer', '__init__.py'),
    description='Generic Python packager for Android / iOS and Desktop',
    long_description=readme + "\n\n" + changelog,
    long_description_content_type='text/markdown',
    author='Mathieu Virbel',
    author_email='mat@kivy.org',
    url='http://github.com/kivy/buildozer',
    license='MIT',
    packages = find_packages(exclude = ['tests*']),
    package_data = package_data,
    include_package_data=True,
    install_requires = Path('requirements.txt').read_text().splitlines(),
    entry_points={
        'console_scripts': [
            'Seizure=buildozer.scripts.client:main',
            'python-for-android=pythonforandroid.entrypoints:main',
            'p4a=pythonforandroid.entrypoints:main',
        ],
        'distutils.commands': [
            'apk = pythonforandroid.bdistapk:BdistAPK',
        ],
    },
)
