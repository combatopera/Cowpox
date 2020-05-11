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

from .logger import logger, Err_Fore, error, info
from fnmatch import fnmatch
from os import getcwd, chdir, makedirs, walk, uname
from os.path import exists, join
from tempfile import mkdtemp
from urllib.request import FancyURLopener
import contextlib, sh, shutil

class WgetDownloader(FancyURLopener):

    version = 'Wget/1.17.1'

urlretrieve = WgetDownloader().retrieve
build_platform = '{system}-{machine}'.format(
    system=uname()[0], machine=uname()[-1]).lower()
"""the build platform in the format `system-machine`. We use
this string to define the right build system when compiling some recipes or
to get the right path for clang compiler"""


@contextlib.contextmanager
def current_directory(new_dir):
    cur_dir = getcwd()
    logger.info(''.join((Err_Fore.CYAN, '-> directory context ', new_dir,
                         Err_Fore.RESET)))
    chdir(new_dir)
    yield
    logger.info(''.join((Err_Fore.CYAN, '<- directory context ', cur_dir,
                         Err_Fore.RESET)))
    chdir(cur_dir)


@contextlib.contextmanager
def temp_directory():
    temp_dir = mkdtemp()
    try:
        logger.debug(''.join((Err_Fore.CYAN, ' + temp directory used ',
                              temp_dir, Err_Fore.RESET)))
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir)
        logger.debug(''.join((Err_Fore.CYAN, ' - temp directory deleted ',
                              temp_dir, Err_Fore.RESET)))


def ensure_dir(filename):
    if not exists(filename):
        makedirs(filename)


def get_virtualenv_executable():
    virtualenv = None
    if virtualenv is None:
        virtualenv = sh.which('virtualenv2')
    if virtualenv is None:
        virtualenv = sh.which('virtualenv-2.7')
    if virtualenv is None:
        virtualenv = sh.which('virtualenv')
    return virtualenv


def walk_valid_filens(base_dir, invalid_dir_names, invalid_file_patterns):
    """Recursively walks all the files and directories in ``dirn``,
    ignoring directories that match any pattern in ``invalid_dirns``
    and files that patch any pattern in ``invalid_filens``.

    ``invalid_dirns`` and ``invalid_filens`` should both be lists of
    strings to match. ``invalid_dir_patterns`` expects a list of
    invalid directory names, while ``invalid_file_patterns`` expects a
    list of glob patterns compared against the full filepath.

    File and directory paths are evaluated as full paths relative to ``dirn``.

    """

    for dirn, subdirs, filens in walk(base_dir):

        # Remove invalid subdirs so that they will not be walked
        for i in reversed(range(len(subdirs))):
            subdir = subdirs[i]
            if subdir in invalid_dir_names:
                subdirs.pop(i)

        for filen in filens:
            for pattern in invalid_file_patterns:
                if fnmatch(filen, pattern):
                    break
            else:
                yield join(dirn, filen)

class BuildInterruptingException(Exception):

    def __init__(self, message, instructions = None):
        super().__init__(message, instructions)
        self.message = message
        self.instructions = instructions

def handle_build_exception(exception):
    """
    Handles a raised BuildInterruptingException by printing its error
    message and associated instructions, if any, then exiting.
    """
    error('Build failed: {}'.format(exception.message))
    if exception.instructions is not None:
        info('Instructions: {}'.format(exception.instructions))
    exit(1)