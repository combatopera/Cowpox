from aridimpl.grammar import templateparser
from aridimpl.model import Concat, Function, Text
from lagoon import git
from pkg_resources import resource_string

charset = 'utf-8'

def processresource(context, *resolvables):
    return Concat(templateparser(resource_string(*(r.resolve(context).cat() for r in resolvables)).decode(charset))).resolve(context)

def githash(context):
    return Text(git.rev_parse.__short.HEAD(cwd = '/src').rstrip())

def lower(context, resolvable):
    return Text(resolvable.resolve(context).cat().lower())

def configure(context):
    for f in processresource, githash, lower:
        context[f.__name__,] = Function(f)
