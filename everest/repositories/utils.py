"""
Repository utilities.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 17, 2013.
"""
from everest.repositories.interfaces import IRepository
from pyramid.threadlocal import get_current_registry
from threading import Lock
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.interface.interfaces import IInterface # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['GlobalObjectManager',
           'commit_veto',
           'get_engine',
           'is_engine_initialized',
           'reset_engines',
           'set_engine',
           ]


class GlobalObjectManager(object):
    _globs = None
    _lock = None

    @classmethod
    def set(cls, key, obj):
        """
        Sets the given object as global object for the given key.
        """
        with cls._lock:
            if not cls._globs.get(key) is None:
                raise ValueError('Duplicate key "%s".' % key)
            cls._globs[key] = obj
        return cls._globs[key]

    @classmethod
    def get(cls, key):
        """
        Returns the global object for the given key.

        :raises KeyError: if no global object was initialized for the given
          key.
        """
        with cls._lock:
            return cls._globs[key]

    @classmethod
    def is_initialized(cls, key):
        """
        Checks if a global object with the given key has been initialized.
        """
        with cls._lock:
            return not cls._globs.get(key) is None

    @classmethod
    def reset(cls):
        """
        Discards all global objects held by this manager.
        """
        with cls._lock:
            cls._globs.clear()


class _DbEngineManager(GlobalObjectManager):
    _globs = {}
    _lock = Lock()

get_engine = _DbEngineManager.get
set_engine = _DbEngineManager.set
is_engine_initialized = _DbEngineManager.is_initialized
reset_engines = _DbEngineManager.reset


def as_repository(resource):
    """
    Adapts the given registered resource to its configured repository.

    :return: object implementing
      :class:`everest.repositories.interfaces.IRepository`.
    """
    reg = get_current_registry()
    if IInterface in provided_by(resource):
        resource = reg.getUtility(resource, name='collection-class')
    return reg.getAdapter(resource, IRepository)


def commit_veto(request, response): # unused request arg pylint: disable=W0613
    """
    Strict commit veto to use with the transaction manager.

    Unlike the default commit veto supplied with the transaction manager,
    this will veto all commits for HTTP status codes other than 2xx unless
    a commit is explicitly requested by setting the "x-tm" response header to
    "commit". As with the default commit veto, the commit is always vetoed if
    the "x-tm" response header is set to anything other than "commit".
    """
    tm_header = response.headers.get('x-tm')
    if not tm_header is None:
        result = tm_header != 'commit'
    else:
        result = not response.status.startswith('2') \
                 and not tm_header == 'commit'
    return result
