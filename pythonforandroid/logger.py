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

from collections import defaultdict
from colorama import Style as Colo_Style, Fore as Colo_Fore
from math import log10
from sys import stdout, stderr
import logging, os, re, sh

log = logging.getLogger(__name__)
# monkey patch to show full output
sh.ErrorReturnCode.truncate_cap = 999999

class LevelDifferentiatingFormatter(logging.Formatter):
    def format(self, record):
        if record.levelno > 30:
            record.msg = '{}{}[ERROR]{}{}:   '.format(
                Err_Style.BRIGHT, Err_Fore.RED, Err_Fore.RESET,
                Err_Style.RESET_ALL) + record.msg
        elif record.levelno > 20:
            record.msg = '{}{}[WARNING]{}{}: '.format(
                Err_Style.BRIGHT, Err_Fore.RED, Err_Fore.RESET,
                Err_Style.RESET_ALL) + record.msg
        elif record.levelno > 10:
            record.msg = '{}[INFO]{}:    '.format(
                Err_Style.BRIGHT, Err_Style.RESET_ALL) + record.msg
        else:
            record.msg = '{}{}[DEBUG]{}{}:   '.format(
                Err_Style.BRIGHT, Err_Fore.LIGHTBLACK_EX, Err_Fore.RESET,
                Err_Style.RESET_ALL) + record.msg
        return super().format(record)

logger = logging.getLogger('p4a')
# Necessary as importlib reloads this,
# which would add a second handler and reset the level
if not hasattr(logger, 'touched'):
    logger.setLevel(logging.DEBUG)
    logger.touched = True
    ch = logging.StreamHandler(stderr)
    formatter = LevelDifferentiatingFormatter('%(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

class colorama_shim:

    def __init__(self, real):
        self._dict = defaultdict(str)
        self._real = real
        self._enabled = False

    def __getattr__(self, key):
        return getattr(self._real, key) if self._enabled else self._dict[key]

    def enable(self, enable):
        self._enabled = enable

Out_Style = colorama_shim(Colo_Style)
Out_Fore = colorama_shim(Colo_Fore)
Err_Style = colorama_shim(Colo_Style)
Err_Fore = colorama_shim(Colo_Fore)

def _shorten_string(string, max_width):
    ''' make limited length string in form:
      "the string is very lo...(and 15 more)"
    '''
    string_len = len(string)
    if string_len <= max_width:
        return string
    visible = max_width - 16 - int(log10(string_len))
    # expected suffix len "...(and YYYYY more)"
    if not isinstance(string, str):
        visstring = str(string[:visible], errors='ignore')
    else:
        visstring = string[:visible]
    return u''.join((visstring, u'...(and ', str(string_len - visible), u' more)'))

def _get_console_width():
    try:
        cols = int(os.environ['COLUMNS'])
    except (KeyError, ValueError):
        pass
    else:
        if cols >= 25:
            return cols
    try:
        cols = max(25, int(os.popen('stty size', 'r').read().split()[1]))
    except Exception:
        pass
    else:
        return cols
    return 100

def shprint(command, *args, **kwargs):
    '''Runs the command (which should be an sh.Command instance), while
    logging the output.'''
    kwargs["_iter"] = True
    kwargs["_out_bufsize"] = 1
    kwargs["_err_to_out"] = True
    kwargs["_bg"] = True
    is_critical = kwargs.pop('_critical', False)
    tail_n = kwargs.pop('_tail', None)
    if "P4A_FULL_DEBUG" in os.environ:
        tail_n = 0
    filter_in = kwargs.pop('_filter', None)
    filter_out = kwargs.pop('_filterout', None)
    columns = _get_console_width()
    command_path = str(command).split('/')
    command_string = command_path[-1]
    string = ' '.join(['{}->{} running'.format(Out_Fore.LIGHTBLACK_EX,
                                               Out_Style.RESET_ALL),
                       command_string] + list(args))
    log.debug("%s%s", string, Err_Style.RESET_ALL)
    need_closing_newline = False
    try:
        output = command(*args, **kwargs)
        for line in output:
            if isinstance(line, bytes):
                line = line.decode('utf-8', errors='replace')
            log.debug("\t%s", line.rstrip())
        if need_closing_newline:
            stdout.write('{}\r{:>{width}}\r'.format(
                Err_Style.RESET_ALL, ' ', width=(columns - 1)))
            stdout.flush()
    except sh.ErrorReturnCode as err:
        if need_closing_newline:
            stdout.write('{}\r{:>{width}}\r'.format(
                Err_Style.RESET_ALL, ' ', width=(columns - 1)))
            stdout.flush()
        if tail_n is not None or filter_in or filter_out:
            def printtail(out, name, forecolor, tail_n=0,
                          re_filter_in=None, re_filter_out=None):
                lines = out.splitlines()
                if re_filter_in is not None:
                    lines = [l for l in lines if re_filter_in.search(l)]
                if re_filter_out is not None:
                    lines = [l for l in lines if not re_filter_out.search(l)]
                if tail_n == 0 or len(lines) <= tail_n:
                    log.info("%s:\n%s\t%s%s", name, forecolor, '\t\n'.join(lines), Out_Fore.RESET)
                else:
                    log.info("%s (last %s lines of %s):\n%s\t%s%s", name, tail_n, len(lines), forecolor, '\t\n'.join(lines[-tail_n:]), Out_Fore.RESET)
            printtail(err.stdout.decode('utf-8'), 'STDOUT', Out_Fore.YELLOW, tail_n,
                      re.compile(filter_in) if filter_in else None,
                      re.compile(filter_out) if filter_out else None)
            printtail(err.stderr.decode('utf-8'), 'STDERR', Err_Fore.RED)
        if is_critical:
            env = kwargs.get("env")
            if env is not None:
                log.info("%sENV:%s\n%s\n", Err_Fore.YELLOW, Err_Fore.RESET, "\n".join(f"set {n}={v}" for n, v in env.items()))
            log.info("%sCOMMAND:%s\ncd %s && %s %s\n", Err_Fore.YELLOW, Err_Fore.RESET, os.getcwd(), command, ' '.join(args))
            log.warning("%sERROR: %s failed!%s", Err_Fore.RED, command, Err_Fore.RESET)
            exit(1)
        else:
            raise
    return output
