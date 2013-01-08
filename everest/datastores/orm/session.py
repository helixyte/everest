"""
Session for the RDBMS backend.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 8, 2013.
"""
from everest.datastores.base import SessionFactory
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session as SaSession
from zope.sqlalchemy import ZopeTransactionExtension  # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['OrmSessionFactory',
           ]


class SaAutocommittingSession(SaSession):
    """
    A session in 'autocommit' mode that automatically commits on 
    :method:`add`, :method:`delete` and :method:`merge` operations.
    """
    def __init__(self, **kw):
        kw['autocommit'] = True
        SaSession.__init__(self, **kw)

    def add(self, entity):
        self.begin()
        SaSession.add(self, entity)
        self.commit()

    def delete(self, entity):
        self.begin()
        SaSession.delete(self, entity)
        self.commit()

    def merge(self, entity, load=True):
        self.begin()
        SaSession.merge(self, entity, load=load)
        self.commit()


# : The scoped session maker. Instantiate this to obtain a thread local
# : session instance.
ScopedSessionMaker = scoped_session(sessionmaker())


class OrmSessionFactory(SessionFactory):
    """
    Factory for ORM data store sessions.
    """
    def __init__(self, entity_store):
        SessionFactory.__init__(self, entity_store)
        if self._entity_store.autocommit:
            # Use an autocommitting Session class with our session factory.
            self.__fac = scoped_session(
                                sessionmaker(class_=SaAutocommittingSession))
        else:
            # Use the default Session factory.
            self.__fac = ScopedSessionMaker

    def configure(self, **kw):
        self.__fac.configure(**kw)

    def __call__(self):
        if not self.__fac.registry.has():
            self.__fac.configure(autoflush=self._entity_store.autoflush)
            if not self._entity_store.autocommit \
               and self._entity_store.join_transaction:
                # Enable the Zope transaction extension with the standard
                # sqlalchemy Session class.
                self.__fac.configure(extension=ZopeTransactionExtension())
        return self.__fac()
