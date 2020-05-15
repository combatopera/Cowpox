from .dirs import Dirs
from diapyr import types
import logging, os, subprocess

log = logging.getLogger(__name__)

class Cmd:

    @types(Dirs)
    def __init__(self, dirs):
        self.environ = dict(PATH = f"{dirs.apache_ant_dir / 'bin'}{os.pathsep}{os.environ['PATH']}")

    def __call__(self, command, stdout = None, check = True, cwd = None):
        log.debug('Run %r', command)
        log.debug('Cwd %s', cwd)
        return subprocess.run(command, shell = True, cwd = cwd, env = {**os.environ, **self.environ}, stdout = stdout, check = check, text = True)
