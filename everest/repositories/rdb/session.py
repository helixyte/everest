"""
Session for the RDBMS backend.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 8, 2013.
"""
from everest.entities.interfaces import IEntity
from everest.entities.traversal import AruVisitor
from everest.exceptions import NoResultsException
from everest.repositories.base import AutocommittingSessionMixin
from everest.repositories.base import Session
from everest.repositories.base import SessionFactory
from everest.traversers import SourceTargetDataTreeTraverser
from everest.utils import set_nested_attribute
from pyramid.compat import iteritems_
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session as SaSession
from zope.sqlalchemy import ZopeTransactionExtension # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['RdbAutocommittingSession',
           'RdbSession',
           'RdbSessionFactory',
           ]


class RdbSession(Session, SaSession):
    """
    Special session class adapting the SQLAlchemy session for everest.
    """
    def __init__(self, *args, **options):
        self.__repository = options.pop('repository')
        SaSession.__init__(self, *args, **options)

    def get_by_id(self, entity_class, id_key):
        try:
            ent = self.query(entity_class).get(id_key)
        except NoResultsException:
            ent = None
        return ent

    def add(self, entity_class, data):
        if not IEntity.providedBy(data): # pylint: disable=E1101
            entity = self.__run_traversal(entity_class, data, None)
        else:
            entity = data
        SaSession.add(self, entity)

    def remove(self, entity_class, data):
        if not IEntity.providedBy(data): # pylint: disable=E1101
            entity = self.__run_traversal(entity_class, None, data)
        else:
            entity = data
        SaSession.delete(self, entity)

    def update(self, entity_class, source_data, target_entity):
        self.__run_traversal(entity_class, source_data, target_entity)
        return target_entity

    def query(self, entity_class):
        return SaSession.query(self, entity_class)

    def __run_traversal(self, entity_class, source, target):
        agg = self.__repository.get_aggregate(entity_class)
        trv = SourceTargetDataTreeTraverser.make_traverser(
                                    source, target, agg,
                                    manage_back_references=False)
        vst = AruVisitor(entity_class, update_callback=self.__update)
        trv.run(vst)
        return vst.root

    def __update(self, entity_class, target_entity, source_data): # pylint: disable=W0613
        for attribute, attr_value in iteritems_(source_data):
            set_nested_attribute(target_entity, attribute.entity_attr,
                                 attr_value)
#        EntityStateManager.set_state_data(entity_class, target_entity,
#                                          source_data)


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
                                 query_cls=self.__query_class,
                                 repository=self._repository)
            if not self._repository.autocommit \
               and self._repository.join_transaction:
                # Enable the Zope transaction extension with the standard
                # sqlalchemy Session class.
                self.__fac.configure(extension=ZopeTransactionExtension())
        return self.__fac()
