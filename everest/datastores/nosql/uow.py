"""
Unit of work.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 16, 2013.
"""
from transaction.interfaces import IDataManager
from weakref import WeakSet
from zope.interface import implements # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['UnitOfWork',
           ]


class OBJECT_STATES(object):
    CLEAN = 'CLEAN'
    NEW = 'NEW'
    DELETED = 'DELETED'
    DIRTY = 'DIRTY'


class ObjectStateData(object):
    def __init__(self):
        self.state_hash = None

    def freeze(self, obj):
        self.state_hash = hash(self.__get_state_string(obj))

    def __get_state_string(self, obj):
        # Concatenate all attribute name:value pairs.
        tokens = ['%s:%s' % (k, v)
                  for k, v in obj.__dict__.iteritems()
                  if not k.startswith('_')]
        return ','.join(tokens)


class UnitOfWork(object):
    def __init__(self):
        self.__objects = WeakSet()

    def register_clean(self, entity):
        entity.__everest__.state = OBJECT_STATES.CLEAN
        self.__objects.add(entity)

    def register_new(self, entity):
        entity.__everest__.state = OBJECT_STATES.NEW
        self.__objects.add(entity)

    def register_deleted(self, entity):
        entity.__everest__.state = OBJECT_STATES.DELETED
        self.__objects.add(entity)

    def register_dirty(self, entity):
        entity.__everest__.state = OBJECT_STATES.DIRTY
        self.__objects.add(entity)

    def flush(self):
        pass


class DataManager(object):
    """
    Data manager to plug a :class:`UnitOfWork` into a zope transaction.
    """
    # TODO: implement safepoints.
    implements(IDataManager)

    def __init__(self, uow):
        self.__uow = uow

    def abort(self, trans): # pylint: disable=W0613
        self.__uow.rollback()

    def tpc_begin(self, trans): # pylint: disable=W0613
        self.__uow.flush()

    def commit(self, trans): # pylint: disable=W0613
        self.__uow.commit()

    def tpc_vote(self, trans): # pylint: disable=W0613
        pass

    def tpc_finish(self, trans):
        pass

    def tpc_abort(self, trans): # pylint: disable=W0613
        self.__uow.rollback()

    def sortKey(self):
        return "everest:%d" % id(self.__uow)
