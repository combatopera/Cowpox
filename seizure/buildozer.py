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

from . import BuildozerException, USE_COLOR
from .android import TargetAndroid
from .jsonstore import JsonStore
from configparser import SafeConfigParser
from fnmatch import fnmatch
from lagoon import tar, unzip
from os import walk, makedirs
from os.path import splitext, expanduser
from pathlib import Path
from pprint import pformat
from pythonforandroid.mirror import Mirror
from re import search
from shutil import copyfile, rmtree, copytree, move
from subprocess import Popen, PIPE
from sys import stdout, stderr, exit
import codecs, colorama, fcntl, logging, os, re, select, sys

log = logging.getLogger(__name__)
colorama.init()
RESET_SEQ = colorama.Fore.RESET + colorama.Style.RESET_ALL
COLOR_SEQ = lambda x: x
BOLD_SEQ = ''
BLACK = colorama.Fore.BLACK + colorama.Style.BRIGHT
RED = colorama.Fore.RED
BLUE = colorama.Fore.CYAN
# error, info, debug
LOG_LEVELS_C = RED, BLUE, BLACK
LOG_LEVELS_T = 'EID'

class BuildozerCommandException(BuildozerException):
    '''
    Exception raised when an external command failed.

    See: `Buildozer.cmd()`.
    '''
    pass

class Buildozer:

    ERROR = 0
    INFO = 1
    DEBUG = 2
    targetname = 'android'
    specfilename = 'buildozer.spec'
    global_buildozer_dir = Path.home() / '.buildozer'
    global_platform_dir = global_buildozer_dir / targetname / 'platform'
    global_packages_dir = global_buildozer_dir / targetname / 'packages'
    global_cache_dir = global_buildozer_dir / 'cache'
    root_dir = Path(specfilename).parent.resolve()
    buildozer_dir = root_dir / '.buildozer'
    bin_dir = root_dir / 'bin'
    platform_dir = buildozer_dir / targetname / 'platform'
    app_dir = buildozer_dir / targetname / 'app'
    applibs_dir = buildozer_dir / 'applibs'
    gardenlibs_dir = buildozer_dir / 'libs'

    def __init__(self):
        self.log_level = 2
        self.environ = {}
        self.state = None
        self.build_id = None
        self.config = SafeConfigParser(allow_no_value=True)
        self.config.optionxform = lambda value: value
        self.config.getlist = self._get_config_list
        self.config.getlistvalues = self._get_config_list_values
        self.config.getdefault = self._get_config_default
        self.config.getbooldefault = self._get_config_bool
        self.config.getrawdefault = self._get_config_raw_default
        self.config.read(self.specfilename, 'utf-8')
        set_config_from_envs(self.config)
        try:
            self.log_level = int(self.config.getdefault('buildozer', 'log_level', '2'))
        except Exception:
            pass
        self.target = None

    def prepare_for_build(self):
        assert self.target is not None
        if hasattr(self.target, '_build_prepared'):
            return

        self.info('Preparing build')

        self.info('Check requirements for {0}'.format(self.targetname))
        self.target.check_requirements()

        self.info('Install platform')
        self.target.install_platform()

        self.info('Check application requirements')
        self.check_application_requirements()

        self.info('Check garden requirements')
        self.check_garden_requirements()

        self.info('Compile platform')
        self.target.compile_platform()

        # flag to prevent multiple build
        self.target._build_prepared = True

    def build(self):
        '''Do the build.

        The target can set build_mode to 'release' or 'debug' before calling
        this method.

        (:meth:`prepare_for_build` must have been call before.)
        '''
        assert(self.target is not None)
        assert(hasattr(self.target, '_build_prepared'))

        if hasattr(self.target, '_build_done'):
            return

        # increment the build number
        self.build_id = int(self.state.get('cache.build_id', '0')) + 1
        self.state['cache.build_id'] = str(self.build_id)

        self.info('Build the application #{}'.format(self.build_id))
        self.build_application()

        self.info('Package the application')
        self.target.build_package()

        # flag to prevent multiple build
        self.target._build_done = True

    #
    # Log functions
    #

    def log(self, level, msg):
        if level > self.log_level:
            return
        if USE_COLOR:
            color = COLOR_SEQ(LOG_LEVELS_C[level])
            print(''.join((RESET_SEQ, color, '# ', msg, RESET_SEQ)))
        else:
            print('{} {}'.format(LOG_LEVELS_T[level], msg))

    def debug(self, msg):
        self.log(self.DEBUG, msg)

    def log_env(self, level, env):
        """dump env into debug logger in readable format"""
        self.log(level, "ENVIRONMENT:")
        for k, v in env.items():
            self.log(level, "    {} = {}".format(k, pformat(v)))

    def info(self, msg):
        self.log(self.INFO, msg)

    def error(self, msg):
        self.log(self.ERROR, msg)

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
            self.debug('Run {0!r}'.format(command))
        else:
            if type(command) in (list, tuple):
                self.debug('Run {0!r} ...'.format(command[0]))
            else:
                self.debug('Run {0!r} ...'.format(command.split()[0]))
        self.debug('Cwd {}'.format(kwargs.get('cwd')))

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
            self.error('Command failed: {0}'.format(command))
            self.log_env(self.ERROR, kwargs['env'])
            self.error('')
            self.error('Buildozer failed to execute the last command')
            if self.log_level <= self.INFO:
                self.error('If the error is not obvious, please raise the log_level to 2')
                self.error('and retry the latest command.')
            else:
                self.error('The error might be hidden in the log above this error')
                self.error('Please read the full log, and search for it before')
                self.error('raising an issue with buildozer itself.')
            self.error('In case of a bug report, please add a full log with log_level = 2')
            raise BuildozerCommandException()
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
            self.debug('Run (expect) {0!r}'.format(command))
        else:
            self.debug('Run (expect) {0!r} ...'.format(command.split()[0]))

        self.debug('Cwd {}'.format(kwargs.get('cwd')))
        return spawnu(command, **kwargs)

    def check_build_layout(self):
        self.mkdir(self.global_buildozer_dir)
        self.mkdir(self.global_cache_dir)
        self.mkdir(self.buildozer_dir)
        self.mkdir(self.bin_dir)
        self.mkdir(self.applibs_dir)
        self.state = JsonStore(Path(self.buildozer_dir, 'state.db'))
        self.mkdir(Path(self.global_platform_dir, self.targetname, 'platform'))
        self.mkdir(Path(self.buildozer_dir, self.targetname, 'platform'))
        self.mkdir(Path(self.buildozer_dir, self.targetname, 'app'))

    def check_application_requirements(self):
        '''Ensure the application requirements are all available and ready to be
        packaged as well.
        '''
        requirements = self.config.getlist('app', 'requirements', '')
        target_available_packages = self.target.get_available_packages()
        if target_available_packages is True:
            # target handles all packages!
            return

        # remove all the requirements that the target can compile
        onlyname = lambda x: x.split('==')[0]  # noqa: E731
        requirements = [x for x in requirements if onlyname(x) not in
                        target_available_packages]

        if requirements and hasattr(sys, 'real_prefix'):
            e = self.error
            e('virtualenv is needed to install pure-Python modules, but')
            e('virtualenv does not support nesting, and you are running')
            e('buildozer in one. Please run buildozer outside of a')
            e('virtualenv instead.')
            exit(1)

        # did we already installed the libs ?
        if Path(self.applibs_dir).exists() and self.state.get('cache.applibs', '') == requirements:
            self.debug('Application requirements already installed, pass')
            return

        # recreate applibs
        self.rmdir(self.applibs_dir)
        self.mkdir(self.applibs_dir)

        # ok now check the availability of all requirements
        for requirement in requirements:
            self._install_application_requirement(requirement)

        # everything goes as expected, save this state!
        self.state['cache.applibs'] = requirements

    def _install_application_requirement(self, module):
        self._ensure_virtualenv()
        self.debug('Install requirement {} in virtualenv'.format(module))
        self.cmd('pip install --target={} {}'.format(self.applibs_dir, module),
                 env=self.env_venv,
                 cwd=self.buildozer_dir)

    def check_garden_requirements(self):
        '''Ensure required garden packages are available to be included.
        '''
        garden_requirements = self.config.getlist('app',
                'garden_requirements', '')

        # have we installed the garden packages?
        if Path(self.gardenlibs_dir).exists() and self.state.get('cache.gardenlibs', '') == garden_requirements:
            self.debug('Garden requirements already installed, pass')
            return

        # we're going to reinstall all the garden libs.
        self.rmdir(self.gardenlibs_dir)

        # but if we don't have requirements, or if the user removed everything,
        # don't do anything.
        if not garden_requirements:
            self.state['cache.gardenlibs'] = garden_requirements
            return

        self._ensure_virtualenv()
        self.cmd('pip install Kivy-Garden==0.1.1', env=self.env_venv)

        # recreate gardenlibs
        self.mkdir(self.gardenlibs_dir)

        for requirement in garden_requirements:
            self._install_garden_package(requirement)

        # save gardenlibs state
        self.state['cache.gardenlibs'] = garden_requirements

    def _install_garden_package(self, package):
        self._ensure_virtualenv()
        self.debug('Install garden package {} in buildozer_dir'.format(package))
        self.cmd('garden install --app {}'.format(package),
                env=self.env_venv,
                cwd=self.buildozer_dir)

    def _ensure_virtualenv(self):
        if hasattr(self, 'venv'):
            return
        self.venv = Path(self.buildozer_dir, 'venv')
        if not self.venv.exists():
            self.cmd('virtualenv --python=python2.7 ./venv',
                    cwd=self.buildozer_dir)

        # read virtualenv output and parse it
        output = self.cmd('bash -c "source venv/bin/activate && env"',
                get_stdout=True,
                cwd=self.buildozer_dir)
        self.env_venv = self.environ.copy()
        for line in output[0].splitlines():
            args = line.split('=', 1)
            if len(args) != 2:
                continue
            key, value = args
            if key in ('VIRTUAL_ENV', 'PATH'):
                self.env_venv[key] = value
        if 'PYTHONHOME' in self.env_venv:
            del self.env_venv['PYTHONHOME']

        # ensure any sort of compilation will fail
        self.env_venv['CC'] = '/bin/false'
        self.env_venv['CXX'] = '/bin/false'

    def mkdir(self, dn):
        if Path(dn).exists():
            return
        self.debug('Create directory {0}'.format(dn))
        makedirs(dn)

    def rmdir(self, dn):
        if not Path(dn).exists():
            return
        self.debug('Remove directory and subdirectory {}'.format(dn))
        rmtree(dn)

    def file_matches(self, patterns):
        from glob import glob
        result = []
        for pattern in patterns:
            matches = glob(expanduser(pattern.strip()))
            result.extend(matches)
        return result

    def file_rename(self, source, target, cwd=None):
        if cwd:
            source = Path(cwd, source)
            target = Path(cwd, target)
        self.debug('Rename {0} to {1}'.format(source, target))
        if not target.parent.is_dir():
            self.error(('Rename {0} to {1} fails because {2} is not a '
                        'directory').format(source, target, target))
        move(source, target)

    def file_copy(self, source, target, cwd=None):
        if cwd:
            source = Path(cwd, source)
            target = Path(cwd, target)
        self.debug('Copy {0} to {1}'.format(source, target))
        copyfile(source, target)

    def file_extract(self, archive, cwd):
        if archive.endswith('.tar.gz'):
            tar.xzf.print(archive, cwd = cwd)
        elif archive.endswith('.zip'):
            unzip._q.print(archive, cwd = cwd)
        else:
            raise Exception(f"Unhandled extraction for type {archive}")

    def file_copytree(self, src, dest):
        print('copy {} to {}'.format(src, dest))
        if os.path.isdir(src):
            if not os.path.isdir(dest):
                os.makedirs(dest)
            files = os.listdir(src)
            for f in files:
                self.file_copytree(Path(src, f), Path(dest, f))
        else:
            copyfile(src, dest)

    def clean_platform(self):
        self.info('Clean the platform build directory')
        if not Path(self.platform_dir).exists():
            return
        rmtree(self.platform_dir)

    def download(self, url, filename, cwd):
        url = url + filename
        filename = Path(cwd, filename)
        if filename.exists():
            filename.unlink()
        self.debug('Downloading {0}'.format(url))
        Path(filename).symlink_to(Mirror.download(url))
        return filename

    def get_version(self):
        c = self.config
        has_version = c.has_option('app', 'version')
        has_regex = c.has_option('app', 'version.regex')
        has_filename = c.has_option('app', 'version.filename')

        # version number specified
        if has_version:
            if has_regex or has_filename:
                raise Exception(
                    'version.regex and version.filename conflict with version')
            return c.get('app', 'version')

        # search by regex
        if has_regex or has_filename:
            if has_regex and not has_filename:
                raise Exception('version.filename is missing')
            if has_filename and not has_regex:
                raise Exception('version.regex is missing')

            fn = c.get('app', 'version.filename')
            with open(fn) as fd:
                data = fd.read()
                regex = c.get('app', 'version.regex')
                match = search(regex, data)
                if not match:
                    raise Exception(
                        'Unable to find capture version in {0}\n'
                        ' (looking for `{1}`)'.format(fn, regex))
                version = match.groups()[0]
                self.debug('Captured version: {0}'.format(version))
                return version

        raise Exception('Missing version or version.regex + version.filename')

    def build_application(self):
        self._copy_application_sources()
        self._copy_application_libs()
        self._copy_garden_libs()
        self._add_sitecustomize()

    def _copy_application_sources(self):
        # xxx clean the inclusion/exclusion algo.
        source_dir = Path(self.config.getdefault('app', 'source.dir', '.')).resolve()
        include_exts = self.config.getlist('app', 'source.include_exts', '')
        exclude_exts = self.config.getlist('app', 'source.exclude_exts', '')
        exclude_dirs = self.config.getlist('app', 'source.exclude_dirs', '')
        exclude_patterns = self.config.getlist('app', 'source.exclude_patterns', '')
        include_patterns = self.config.getlist('app',
                                               'source.include_patterns',
                                               '')
        app_dir = self.app_dir

        self.debug('Copy application source from {}'.format(source_dir))

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
                rfn = Path(app_dir, root[len(str(source_dir)) + 1:], fn).resolve()
                self.mkdir(rfn.parent)
                self.debug('Copy {0}'.format(sfn))
                copyfile(sfn, rfn)

    def _copy_application_libs(self):
        # copy also the libs
        copytree(self.applibs_dir, Path(self.app_dir, '_applibs'))

    def _copy_garden_libs(self):
        if Path(self.gardenlibs_dir).exists():
            copytree(self.gardenlibs_dir, Path(self.app_dir, 'libs'))

    def _add_sitecustomize(self):
        copyfile(Path(__file__).parent / 'sitecustomize.py', self.app_dir / 'sitecustomize.py')
        main_py = self.app_dir / 'service' / 'main.py'
        if not main_py.exists():
            #self.error('Unable to patch main_py to add applibs directory.')
            return

        header = (b'import sys, os; '
                   b'sys.path = [os.path.join(os.getcwd(),'
                   b'"..", "_applibs")] + sys.path\n')
        with open(main_py, 'rb') as fd:
            data = fd.read()
        data = header + data
        with open(main_py, 'wb') as fd:
            fd.write(data)
        self.info('Patched service/main.py to include applibs')

    def namify(self, name):
        '''Return a "valid" name from a name with lot of invalid chars
        (allowed characters: a-z, A-Z, 0-9, -, _)
        '''
        return re.sub('[^a-zA-Z0-9_\-]', '_', name)

    @property
    def package_full_name(self):
        package_name = self.config.getdefault('app', 'package.name', '')
        package_domain = self.config.getdefault('app', 'package.domain', '')
        if package_domain == '':
            return package_name
        return '{}.{}'.format(package_domain, package_name)

    def android_debug(self):
        self.target = TargetAndroid(self)
        self.check_build_layout()
        self.target.run_commands(['debug'])

    def _get_config_list_values(self, *args, **kwargs):
        kwargs['with_values'] = True
        return self._get_config_list(*args, **kwargs)

    def _get_config_list(self, section, token, default=None, with_values=False):
        # monkey-patch method for ConfigParser
        # get a key as a list of string, separated from the comma

        # check if an env var exists that should replace the file config
        set_config_token_from_env(section, token, self.config)

        # if a section:token is defined, let's use the content as a list.
        l_section = '{}:{}'.format(section, token)
        if self.config.has_section(l_section):
            values = self.config.options(l_section)
            if with_values:
                return ['{}={}'.format(key, self.config.get(l_section, key)) for
                        key in values]
            else:
                return [x.strip() for x in values]

        values = self.config.getdefault(section, token, '')
        if not values:
            return default
        values = values.split(',')
        if not values:
            return default
        return [x.strip() for x in values]

    def _get_config_default(self, section, token, default=None):
        # monkey-patch method for ConfigParser
        # get an appropriate env var if it exists, else
        # get a key in a section, or the default

        # check if an env var exists that should replace the file config
        set_config_token_from_env(section, token, self.config)

        if not self.config.has_section(section):
            return default
        if not self.config.has_option(section, token):
            return default
        return self.config.get(section, token)

    def _get_config_bool(self, section, token, default=False):
        # monkey-patch method for ConfigParser
        # get a key in a section, or the default

        # check if an env var exists that should replace the file config
        set_config_token_from_env(section, token, self.config)

        if not self.config.has_section(section):
            return default
        if not self.config.has_option(section, token):
            return default
        return self.config.getboolean(section, token)

    def _get_config_raw_default(self, section, token, default=None, section_sep="=", split_char=" "):
        l_section = '{}:{}'.format(section, token)
        if self.config.has_section(l_section):
            return [section_sep.join(item) for item in self.config.items(l_section)]
        if not self.config.has_option(section, token):
            return default.split(split_char)
        return self.config.get(section, token).split(split_char)


def set_config_from_envs(config):
    '''Takes a ConfigParser, and checks every section/token for an
    environment variable of the form SECTION_TOKEN, with any dots
    replaced by underscores. If the variable exists, sets the config
    variable to the env value.
    '''
    for section in config.sections():
        for token in config.options(section):
            set_config_token_from_env(section, token, config)

def set_config_token_from_env(section, token, config):
    '''Given a config section and token, checks for an appropriate
    environment variable. If the variable exists, sets the config entry to
    its value.

    The environment variable checked is of the form SECTION_TOKEN, all
    upper case, with any dots replaced by underscores.

    Returns True if the environment variable exists and was used, or
    False otherwise.

    '''
    env_var_name = ''.join([section.upper(), '_',
                            token.upper().replace('.', '_')])
    env_var = os.environ.get(env_var_name)
    if env_var is None:
        return False
    config.set(section, token, env_var)
    return True
