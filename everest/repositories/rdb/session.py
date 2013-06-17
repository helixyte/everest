"""
Session for the RDBMS backend.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 8, 2013.
"""
from everest.exceptions import NoResultsException
from everest.repositories.base import AutocommittingSessionMixin
from everest.repositories.base import Session
from everest.repositories.base import SessionFactory
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session as SaSession
from zope.sqlalchemy import ZopeTransactionExtension # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['RdbSessionFactory',
           ]


class RdbSession(Session, SaSession):
    """
    Special session class adapting the SQLAlchemy session for everest.
    """
    def get_by_id(self, entity_class, id_key):
        try:
            ent = self.query(entity_class).get(id_key)
        except NoResultsException:
            ent = None
        return ent

    def add(self, entity_class, entity):
        SaSession.add(self, entity)

    def remove(self, entity_class, entity):
        SaSession.delete(self, entity)

    def update(self, entity_class, entity):
        return SaSession.merge(self, entity)

    def query(self, entity_class):
        return SaSession.query(self, entity_class)


class RdbAutocommittingSession(AutocommittingSessionMixin, RdbSession):
    def __init__(self, **kw):
        kw['autocommit'] = True
        super(RdbAutocommittingSession, self).__init__(**kw)


#: The scoped session maker. Instantiate this to obtain a thread local
#: session instance.
ScopedSessionMaker = scoped_session(sessionmaker(class_=RdbSession))


class RdbSessionFactory(SessionFactory):
    """
    Factory for RDB repository sessions.
    """
    def __init__(self, repository, query_class):
        SessionFactory.__init__(self, repository)
        if self._repository.autocommit:
            # Use an autocommitting Session class with our session factory.
            self.__fac = scoped_session(
                                sessionmaker(class_=RdbAutocommittingSession))
        else:
            # Use the default Session factory.
            self.__fac = ScopedSessionMaker
        self.__query_class = query_class

    def configure(self, **kw):
        self.__fac.configure(**kw)

    def __call__(self):
        if not self.__fac.registry.has():
            self.__fac.configure(autoflush=self._repository.autoflush,
                                 query_cls=self.__query_class)
            if not self._repository.autocommit \
               and self._repository.join_transaction:
                # Enable the Zope transaction extension with the standard
                # sqlalchemy Session class.
                self.__fac.configure(extension=ZopeTransactionExtension())
        return self.__fac()
