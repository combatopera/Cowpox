from diapyr import types
import logging, os, subprocess

log = logging.getLogger(__name__)

class Cmd:

    @types()
    def __init__(self):
        self.environ = {}

    def __call__(self, command, stdout = None, check = True, cwd = None):
        log.debug('Run %r', command)
        log.debug('Cwd %s', cwd)
        return subprocess.run(command, shell = True, cwd = cwd, env = {**os.environ, **self.environ}, stdout = stdout, check = check, text = True)
