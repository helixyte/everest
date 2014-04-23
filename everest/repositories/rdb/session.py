"""
Session for the rdb backend.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 8, 2013.
"""
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.query import Query
from sqlalchemy.orm.session import Session as SaSession

from everest.constants import RELATION_OPERATIONS
from everest.entities.interfaces import IEntity
from everest.entities.traversal import AruVisitor
from everest.repositories.base import AutocommittingSessionMixin
from everest.repositories.base import Session
from everest.repositories.base import SessionFactory
from everest.repositories.state import EntityState
from everest.traversal import SourceTargetDataTreeTraverser
from zope.sqlalchemy import ZopeTransactionExtension # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['RdbAutocommittingSession',
           'RdbSession',
           'RdbSessionFactory',
           'ScopedSessionMaker',
           ]


class RdbSession(SaSession, Session):
    """
    Special session class adapting the SQLAlchemy session for everest.
    """
    IS_MANAGING_BACKREFERENCES = False

    def __init__(self, *args, **options):
        self.__repository = options.pop('repository')
        SaSession.__init__(self, *args, **options)

    def get_by_id(self, entity_class, id_key):
        return self.query(entity_class).get(id_key)

    def get_by_slug(self, entity_class, slug):
        # We don't have an optimization for access by slug here; returning
        # `None` indicates that a query should be run.
        return None

    def add(self, entity_class, data): # different signature pylint: disable=W0222
        if not IEntity.providedBy(data): # pylint: disable=E1101
            self.__run_traversal(entity_class, data, None,
                                 RELATION_OPERATIONS.ADD)
        else:
            SaSession.add(self, data)

    def remove(self, entity_class, data):
        if not IEntity.providedBy(data): # pylint: disable=E1101
            self.__run_traversal(entity_class, None, data,
                                 RELATION_OPERATIONS.REMOVE)
        else:
            SaSession.delete(self, data)

    def update(self, entity_class, data, target=None):
        if not IEntity.providedBy(data): # pylint: disable=E1101
            upd_ent = self.__run_traversal(entity_class, data, target,
                                           RELATION_OPERATIONS.UPDATE)
        else:
            upd_ent = SaSession.merge(self, data)
        return upd_ent

    def query(self, *entities, **options):
        # When called by everest from an aggregate, we use the counting query
        # class that attempts to fetch the total result count and the first
        # result page in one call here.
        query_cls = options.pop('query_class', Query)
        return query_cls(entities, self, **options)

    def reset(self):
        self.rollback()
        self.expunge_all()

    def __run_traversal(self, entity_class, source_data, target_data, rel_op):
        agg = self.__repository.get_aggregate(entity_class)
        trv = SourceTargetDataTreeTraverser.make_traverser(
                                    source_data, target_data, rel_op,
                                    accessor=agg,
                                    manage_back_references=False)
        vst = AruVisitor(entity_class,
                         add_callback=self.__add,
                         remove_callback=self.__remove,
                         update_callback=self.__update,
                         pass_path_to_callbacks=True)
        trv.run(vst)
        return vst.root

    def __add(self, entity_class, entity, path): # pylint: disable=W0613
        if len(path) == 0:
            SaSession.add(self, entity)

    def __remove(self, entity_class, entity, path): # pylint: disable=W0613
        if len(path) == 0:
            SaSession.delete(self, entity)

    def __update(self, entity_class, source_data, target_entity, path): # pylint: disable=W0613
        EntityState.set_state_data(target_entity, source_data)


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
    def __init__(self, repository, counting_query_class):
        SessionFactory.__init__(self, repository)
        if self._repository.autocommit:
            # Use an autocommitting Session class with our session factory.
            self.__fac = scoped_session(
                                sessionmaker(class_=RdbAutocommittingSession))
        else:
            # Use the default Session factory.
            self.__fac = ScopedSessionMaker
        #: This is the (optimized, if the engine supports it) counting query
        #: class used for paged queries.
        self.counting_query_class = counting_query_class

    def configure(self, **kw):
        self.__fac.configure(**kw)

    def __call__(self, **kw):
        if not self.__fac.registry.has():
            self.__fac.configure(
                            autoflush=self._repository.autoflush,
                            repository=self._repository)
            if not self._repository.autocommit \
               and self._repository.join_transaction:
                # Enable the Zope transaction extension.
                self.__fac.configure(extension=ZopeTransactionExtension())
            else:
                # Disable extension otherwise.
                self.__fac.configure(extension=None)
        return self.__fac(**kw)
