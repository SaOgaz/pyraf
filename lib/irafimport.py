"""module irafimport.py -- modify import mechanism

Modify module import mechanism so that
(1) 'from iraf import pkg' automatically loads the IRAF package 'pkg'
(2) 'import iraf' returns a wrapped module instance that allows minimum-match
        access to task names (e.g. iraf.imhead, not just iraf.imheader)

Assumes that all IRAF tasks and packages are accessible as iraf
module attributes.  Only affects imports of iraf module.

$Id$

R. White, 1999 August 17
"""
from __future__ import division # confidence high

import __builtin__
import sys
from pytools import minmatch

_importHasLvlArg = sys.version_info[0] > 2 or sys.version_info[1] >= 5 # no 1.*
_reloadIsBuiltin = sys.version_info[0] < 3

# Save the original hooks;  replaced at bottom of module...
_originalImport = __builtin__.__import__
if _reloadIsBuiltin:
    _originalReload = __builtin__.reload
else:
    import imp
    _originalReload = imp.reload


def restoreBuiltins():
    """ Called before exiting pyraf - this puts import and reload back. """
    __builtin__.__import__ = _originalImport
    if _reloadIsBuiltin:
        __builtin__.reload = _originalReload
    else:
        imp.reload = _originalReload


def _irafImport(name, globals={}, locals={}, fromlist=[], level=-1):
    if fromlist and (name in ["iraf", "pyraf.iraf"]):
        for task in fromlist:
            pkg = iraf.getPkg(task,found=1)
            if pkg is not None and not pkg.isLoaded():
                pkg.run(_doprint=0, _hush=1)
        # must return a module for 'from' import
        return _irafModuleProxy.module
    elif name == "iraf":
        return _irafModuleProxy
    else:
        # !!! TEMPORARY KLUDGE !!! working on why seeing pyraf.minmatch in cache
        if   name == 'pyraf.minmatch':  name = 'pytools.minmatch'
        elif name == 'pyraf.irafutils': name = 'pytools.irafutils'
        elif name == 'pyraf.dialog':    name = 'pytools.dialog'
        elif name == 'pyraf.listdlg':   name = 'pytools.listdlg'
        elif name == 'pyraf.filedlg':   name = 'pytools.filedlg'
        elif name == 'pyraf.alert':     name = 'pytools.alert'
        elif name == 'pyraf.irafglobals': name='pytools.irafglobals' # is diffnt
        # Not planning to fix this until after 'pytools' is renamed.
        # !!! END TEMPORARY KLUDGE !!!

        if _importHasLvlArg:
            return _originalImport(name, globals, locals, fromlist, level)
        else:
            # we could assert here that level == -1, but it's safe to assume
            return _originalImport(name, globals, locals, fromlist)

def _irafReload(module):
    if isinstance(module, _irafModuleClass):
        #XXX Not sure this is correct
        module.module = _originalReload(module.module)
        return module
    else:
        return _originalReload(module)


class _irafModuleClass:
    """Proxy for iraf module that makes tasks appear as attributes"""
    def __init__(self):
        self.__dict__['module'] = None

    def _moduleInit(self):
        global iraf
        self.__dict__['module'] = iraf
        self.__dict__['__name__'] = iraf.__name__
        # create minmatch dictionary of current module contents
        self.__dict__['mmdict'] = minmatch.MinMatchDict(vars(self.module))

    def __getattr__(self, attr):
        if self.module is None: self._moduleInit()
        # first try getting this attribute directly from the usual module
        try:
            return getattr(self.module, attr)
        except AttributeError:
            pass
        # if that fails, try getting a task with this name
        try:
            return self.module.getTask(attr)
        except minmatch.AmbiguousKeyError, e:
            raise AttributeError(str(e))
        except KeyError, e:
            pass
        # last try is minimum match dictionary of rest of module contents
        try:
            return self.mmdict[attr]
        except KeyError:
            raise AttributeError("Undefined IRAF task `%s'" % (attr,))

    def __setattr__(self, attr, value):
        # add an attribute to the module itself
        setattr(self.module, attr, value)
        self.mmdict.add(attr, value)

    def getAllMatches(self, taskname):
        """Get list of names of all tasks that may match taskname

        Useful for command completion.
        """
        if self.module is None: self._moduleInit()
        if taskname == "":
            matches = self.mmdict.keys()
        else:
            matches = self.mmdict.getallkeys(taskname, [])
        matches.extend(self.module.getAllTasks(taskname))
        return matches


# Install our hooks
__builtin__.__import__ = _irafImport
if _reloadIsBuiltin:
    __builtin__.reload = _irafReload
else:
    imp.reload = _irafReload

# create the module proxy
_irafModuleProxy = _irafModuleClass()

# import iraf module using original mechanism
iraf = _originalImport('iraf', globals(), locals(), [])
