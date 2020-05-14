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

from .android import TargetAndroid
from .jsonstore import JsonStore
from fnmatch import fnmatch
from os import walk
from os.path import splitext
from pathlib import Path
from shutil import copyfile, rmtree, copytree
from subprocess import Popen, PIPE
from sys import stdout, stderr
import colorama, fcntl, logging, os, select

log = logging.getLogger(__name__)
colorama.init()
COLOR_SEQ = lambda x: x
BOLD_SEQ = ''
BLACK = colorama.Fore.BLACK + colorama.Style.BRIGHT
RED = colorama.Fore.RED
BLUE = colorama.Fore.CYAN

class Dirs:

    global_buildozer_dir = Path.home() / '.buildozer'
    global_cache_dir = global_buildozer_dir / 'cache' # XXX: Used?
    root_dir = Path.cwd()
    buildozer_dir = root_dir / '.buildozer'
    bin_dir = root_dir / 'bin'
    applibs_dir = buildozer_dir / 'applibs'

    def __init__(self, config):
        self.global_platform_dir = self.global_buildozer_dir / config.targetname / 'platform'
        self.platform_dir = self.buildozer_dir / config.targetname / 'platform'
        self.app_dir = self.buildozer_dir / config.targetname / 'app'

    def install(self):
        for path in self.global_cache_dir, self.bin_dir, self.applibs_dir, self.global_platform_dir, self.platform_dir, self.app_dir:
            path.mkdir(parents = True, exist_ok = True)

class Buildozer:

    def __init__(self, config, dirs):
        self.environ = {}
        self.config = config
        self.dirs = dirs

    def cmd(self, command, **kwargs):
        # prepare the environ, based on the system + our own env
        env = os.environ.copy()
        env.update(self.environ)

        # prepare the process
        kwargs.setdefault('env', env)
        kwargs.setdefault('stdout', PIPE)
        kwargs.setdefault('stderr', PIPE)
        kwargs.setdefault('close_fds', True)
        kwargs.setdefault('shell', True)
        kwargs.setdefault('show_output', True)
        show_output = kwargs.pop('show_output')
        get_stdout = kwargs.pop('get_stdout', False)
        break_on_error = kwargs.pop('break_on_error', True)
        log.debug('Run %r', command)
        log.debug('Cwd %s', kwargs.get('cwd'))
        # open the process
        process = Popen(command, **kwargs)

        # prepare fds
        fd_stdout = process.stdout.fileno()
        fd_stderr = process.stderr.fileno()
        fcntl.fcntl(fd_stdout, fcntl.F_SETFL, fcntl.fcntl(fd_stdout, fcntl.F_GETFL) | os.O_NONBLOCK)
        fcntl.fcntl(fd_stderr, fcntl.F_SETFL, fcntl.fcntl(fd_stderr, fcntl.F_GETFL) | os.O_NONBLOCK)
        ret_stdout = [] if get_stdout else None
        ret_stderr = None
        while True:
            try:
                readx = select.select([fd_stdout, fd_stderr], [], [])[0]
            except select.error:
                break
            if fd_stdout in readx:
                chunk = process.stdout.read()
                if not chunk:
                    break
                if get_stdout:
                    ret_stdout.append(chunk)
                if show_output:
                    stdout.write(chunk.decode('utf-8', 'replace'))
            if fd_stderr in readx:
                chunk = process.stderr.read()
                if not chunk:
                    break
                if show_output:
                    stderr.write(chunk.decode('utf-8', 'replace'))
            stdout.flush()
            stderr.flush()

        process.communicate()
        if process.returncode != 0 and break_on_error:
            log.error('Command failed: %s', command)
            log.error('')
            log.error('Buildozer failed to execute the last command')
            log.error('The error might be hidden in the log above this error')
            log.error('Please read the full log, and search for it before')
            log.error('raising an issue with buildozer itself.')
            log.error('In case of a bug report, please add a full log with log_level = 2')
            raise Exception()
        if ret_stdout:
            ret_stdout = b''.join(ret_stdout)
        if ret_stderr:
            ret_stderr = b''.join(ret_stderr)
        return (ret_stdout.decode('utf-8', 'ignore') if ret_stdout else None,
                ret_stderr.decode('utf-8') if ret_stderr else None,
                process.returncode)

    def _copy_application_sources(self):
        # xxx clean the inclusion/exclusion algo.
        source_dir = Path(self.config.getdefault('app', 'source.dir', '.')).resolve()
        include_exts = self.config.getlist('app', 'source.include_exts', '')
        exclude_exts = self.config.getlist('app', 'source.exclude_exts', '')
        exclude_dirs = self.config.getlist('app', 'source.exclude_dirs', '')
        exclude_patterns = self.config.getlist('app', 'source.exclude_patterns', '')
        include_patterns = self.config.getlist('app', 'source.include_patterns', '')
        log.debug('Copy application source from %s', source_dir)
        rmtree(self.dirs.app_dir)
        for root, dirs, files in walk(source_dir, followlinks=True):
            # avoid hidden directory
            if True in [x.startswith('.') for x in root.split(os.sep)]:
                continue

            # need to have sort-of normalization. Let's say you want to exclude
            # image directory but not images, the filtered_root must have a / at
            # the end, same for the exclude_dir. And then we can safely compare
            filtered_root = root[len(str(source_dir)) + 1:].lower()
            if filtered_root:
                filtered_root += '/'

                # manual exclude_dirs approach
                is_excluded = False
                for exclude_dir in exclude_dirs:
                    if exclude_dir[-1] != '/':
                        exclude_dir += '/'
                    if filtered_root.startswith(exclude_dir.lower()):
                        is_excluded = True
                        break

                # pattern matching
                if not is_excluded:
                    # match pattern if not ruled out by exclude_dirs
                    for pattern in exclude_patterns:
                        if fnmatch(filtered_root, pattern):
                            is_excluded = True
                            break
                for pattern in include_patterns:
                    if fnmatch(filtered_root, pattern):
                        is_excluded = False
                        break

                if is_excluded:
                    continue

            for fn in files:
                # avoid hidden files
                if fn.startswith('.'):
                    continue

                # pattern matching
                is_excluded = False
                dfn = fn.lower()
                if filtered_root:
                    dfn = Path(filtered_root, fn)
                for pattern in exclude_patterns:
                    if fnmatch(dfn, pattern):
                        is_excluded = True
                        break
                for pattern in include_patterns:
                    if fnmatch(dfn, pattern):
                        is_excluded = False
                        break
                if is_excluded:
                    continue

                # filter based on the extension
                # todo more filters
                basename, ext = splitext(fn)
                if ext:
                    ext = ext[1:]
                    if include_exts and ext not in include_exts:
                        continue
                    if exclude_exts and ext in exclude_exts:
                        continue
                sfn = Path(root, fn)
                rfn = (self.dirs.app_dir / root[len(str(source_dir)) + 1:] / fn).resolve()
                rfn.parent.mkdir(parents = True, exist_ok = True)
                log.debug('Copy %s', sfn)
                copyfile(sfn, rfn)

    def _add_sitecustomize(self):
        copyfile(Path(__file__).parent / 'sitecustomize.py', self.dirs.app_dir / 'sitecustomize.py')
        main_py = self.dirs.app_dir / 'service' / 'main.py'
        if not main_py.exists():
            return
        header = (b'import sys, os; '
                   b'sys.path = [os.path.join(os.getcwd(),'
                   b'"..", "_applibs")] + sys.path\n')
        with open(main_py, 'rb') as fd:
            data = fd.read()
        data = header + data
        with open(main_py, 'wb') as fd:
            fd.write(data)
        log.info('Patched service/main.py to include applibs')

    def android_debug(self):
        self.dirs.install()
        target = TargetAndroid(self.config, JsonStore(self.dirs.buildozer_dir / 'state.db'), self, self.dirs, 'debug')
        log.info('Preparing build')
        log.info('Check requirements for %s', self.config.targetname)
        target.check_requirements()
        log.info('Install platform')
        target.install_platform()
        log.info('Compile platform')
        target.compile_platform()
        self._copy_application_sources()
        copytree(self.dirs.applibs_dir, self.dirs.app_dir / '_applibs')
        self._add_sitecustomize()
        log.info('Package the application')
        target.build_package()
