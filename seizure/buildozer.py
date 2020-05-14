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
from os import walk, makedirs
from os.path import splitext
from pathlib import Path
from shutil import copyfile, rmtree, copytree, move
from subprocess import Popen, PIPE
from sys import stdout, stderr
import codecs, colorama, fcntl, logging, os, select

log = logging.getLogger(__name__)
colorama.init()
COLOR_SEQ = lambda x: x
BOLD_SEQ = ''
BLACK = colorama.Fore.BLACK + colorama.Style.BRIGHT
RED = colorama.Fore.RED
BLUE = colorama.Fore.CYAN

class Buildozer:

    ERROR = 0
    INFO = 1
    DEBUG = 2
    targetname = 'android'
    global_buildozer_dir = Path.home() / '.buildozer'
    global_platform_dir = global_buildozer_dir / targetname / 'platform'
    global_packages_dir = global_buildozer_dir / targetname / 'packages'
    global_cache_dir = global_buildozer_dir / 'cache'
    root_dir = Path.cwd()
    buildozer_dir = root_dir / '.buildozer'
    bin_dir = root_dir / 'bin'
    platform_dir = buildozer_dir / targetname / 'platform'
    app_dir = buildozer_dir / targetname / 'app'
    applibs_dir = buildozer_dir / 'applibs'

    def __init__(self, config):
        self.log_level = 2
        self.environ = {}
        self.config = config
        try:
            self.log_level = int(config.getdefault('buildozer', 'log_level', '2'))
        except Exception:
            pass

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
        kwargs.setdefault('show_output', self.log_level > 1)

        show_output = kwargs.pop('show_output')
        get_stdout = kwargs.pop('get_stdout', False)
        get_stderr = kwargs.pop('get_stderr', False)
        break_on_error = kwargs.pop('break_on_error', True)
        sensible = kwargs.pop('sensible', False)

        if not sensible:
            log.debug('Run %r', command)
        else:
            if type(command) in (list, tuple):
                log.debug('Run %r ...', command[0])
            else:
                log.debug('Run %r ...', command.split()[0])
        log.debug('Cwd %s', kwargs.get('cwd'))
        # open the process
        process = Popen(command, **kwargs)

        # prepare fds
        fd_stdout = process.stdout.fileno()
        fd_stderr = process.stderr.fileno()
        fcntl.fcntl(fd_stdout, fcntl.F_SETFL, fcntl.fcntl(fd_stdout, fcntl.F_GETFL) | os.O_NONBLOCK)
        fcntl.fcntl(fd_stderr, fcntl.F_SETFL, fcntl.fcntl(fd_stderr, fcntl.F_GETFL) | os.O_NONBLOCK)
        ret_stdout = [] if get_stdout else None
        ret_stderr = [] if get_stderr else None
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
                if get_stderr:
                    ret_stderr.append(chunk)
                if show_output:
                    stderr.write(chunk.decode('utf-8', 'replace'))
            stdout.flush()
            stderr.flush()

        process.communicate()
        if process.returncode != 0 and break_on_error:
            log.error('Command failed: %s', command)
            log.error('')
            log.error('Buildozer failed to execute the last command')
            if self.log_level <= self.INFO:
                log.error('If the error is not obvious, please raise the log_level to 2')
                log.error('and retry the latest command.')
            else:
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

    def cmd_expect(self, command, **kwargs):
        from pexpect import spawnu

        # prepare the environ, based on the system + our own env
        env = os.environ.copy()
        env.update(self.environ)

        # prepare the process
        kwargs.setdefault('env', env)
        kwargs.setdefault('show_output', self.log_level > 1)
        sensible = kwargs.pop('sensible', False)
        show_output = kwargs.pop('show_output')

        if show_output:
            kwargs['logfile'] = codecs.getwriter('utf8')(stdout.buffer)
        if not sensible:
            log.debug('Run (expect) %r', command)
        else:
            log.debug('Run (expect) %r ...', command.split()[0])
        log.debug('Cwd %s', kwargs.get('cwd'))
        return spawnu(command, **kwargs)

    def mkdir(self, dn):
        if Path(dn).exists():
            return
        log.debug('Create directory %s', dn)
        makedirs(dn)

    def rmdir(self, dn):
        if not Path(dn).exists():
            return
        log.debug('Remove directory and subdirectory %s', dn)
        rmtree(dn)

    def file_rename(self, source, target, cwd):
        if cwd:
            source = Path(cwd, source)
            target = Path(cwd, target)
        log.debug('Rename %s to %s', source, target)
        if not target.parent.is_dir():
            log.error('Rename %s to %s fails because %s is not a directory', source, target, target)
        move(source, target)

    def file_copy(self, source, target, cwd=None):
        if cwd:
            source = Path(cwd, source)
            target = Path(cwd, target)
        log.debug('Copy %s to %s', source, target)
        copyfile(source, target)

    def _copy_application_sources(self):
        # xxx clean the inclusion/exclusion algo.
        source_dir = Path(self.config.getdefault('app', 'source.dir', '.')).resolve()
        include_exts = self.config.getlist('app', 'source.include_exts', '')
        exclude_exts = self.config.getlist('app', 'source.exclude_exts', '')
        exclude_dirs = self.config.getlist('app', 'source.exclude_dirs', '')
        exclude_patterns = self.config.getlist('app', 'source.exclude_patterns', '')
        include_patterns = self.config.getlist('app', 'source.include_patterns', '')
        log.debug('Copy application source from %s', source_dir)
        rmtree(self.app_dir)
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
                rfn = (self.app_dir / root[len(str(source_dir)) + 1:] / fn).resolve()
                self.mkdir(rfn.parent)
                log.debug('Copy %s', sfn)
                copyfile(sfn, rfn)

    def _add_sitecustomize(self):
        copyfile(Path(__file__).parent / 'sitecustomize.py', self.app_dir / 'sitecustomize.py')
        main_py = self.app_dir / 'service' / 'main.py'
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
        for path in self.global_buildozer_dir, self.global_cache_dir, self.buildozer_dir, self.bin_dir, self.applibs_dir, self.global_platform_dir / self.targetname / 'platform', self.buildozer_dir / self.targetname / 'platform', self.buildozer_dir / self.targetname / 'app':
            path.mkdir(parents = True, exist_ok = True)
        target = TargetAndroid(self.config, JsonStore(self.buildozer_dir / 'state.db'), self, 'debug')
        log.info('Preparing build')
        log.info('Check requirements for %s', self.targetname)
        target.check_requirements()
        log.info('Install platform')
        target.install_platform()
        log.info('Compile platform')
        target.compile_platform()
        self._copy_application_sources()
        copytree(self.applibs_dir, self.app_dir / '_applibs')
        self._add_sitecustomize()
        log.info('Package the application')
        target.build_package()
