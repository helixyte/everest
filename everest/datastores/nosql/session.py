"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 8, 2013.
"""
from everest.datastores.base import SessionFactory
from threading import local
from transaction.interfaces import IDataManager
from zope.interface import implements # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = []


class DataManager(object):
    """
    Data manager to plug an :class:`MemorySession` into a zope transaction.
    """
    # TODO: implement safepoints.
    implements(IDataManager)

    def __init__(self, session):
        self.session = session

    def abort(self, trans): # pylint: disable=W0613
        self.session.rollback()

    def tpc_begin(self, trans): # pylint: disable=W0613
        self.session.flush()

    def commit(self, trans): # pylint: disable=W0613
        self.session.commit()

    def tpc_vote(self, trans): # pylint: disable=W0613
        pass

    def tpc_finish(self, trans):
        pass

    def tpc_abort(self, trans): # pylint: disable=W0613
        self.session.rollback()

    def sortKey(self):
        return "everest:%d" % id(self.session)


class Session(object):
    """
    """
    def __init__(self, unit_of_work):
        self.__unit_of_work = unit_of_work

    def commit(self):
        self.__unit_of_work.commit()

    def rollback(self):
        self.__unit_of_work.rollback()

    def add(self, entity_cls, entity):
        pass

    def remove(self, entity_cls, entity):
        pass

    def get_by_id(self, entity_cls, entity_id):
        pass

    def get_by_slug(self, entity_cls, entity_slug):
        pass

    def get_all(self, entity_cls):
        pass

    def flush(self):
        pass


class MemorySessionFactory(SessionFactory):
    """
    Factory for :class:`MemorySession` instances.
    
    The factory creates exactly one session per thread.
    """
    def __init__(self, entity_store):
        SessionFactory.__init__(self, entity_store)
        self.__session_registry = local()

    def __call__(self):
        session = getattr(self.__session_registry, 'session', None)
        if session is None:
            session = Session(self._entity_store)
            self.__session_registry.session = session
        return session
