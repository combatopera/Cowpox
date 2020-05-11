import os

USE_COLOR = 'NO_COLOR' not in os.environ

class BuildozerException(Exception): pass
