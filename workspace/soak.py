from aridimpl.grammar import templateparser
from aridimpl.model import Concat, Function
from pkg_resources import resource_string

charset = 'utf-8'

def processresource(context, *resolvables):
    return Concat(templateparser(resource_string(*(r.resolve(context).cat() for r in resolvables)).decode(charset))).resolve(context)

def configure(context):
    for f in processresource,:
        context[f.__name__,] = Function(f)
