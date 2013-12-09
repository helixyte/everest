"""
Session for the rdb backend.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 8, 2013.
"""
from everest.constants import RELATION_OPERATIONS
from everest.entities.interfaces import IEntity
from everest.entities.traversal import AruVisitor
from everest.exceptions import NoResultsException
from everest.repositories.base import AutocommittingSessionMixin
from everest.repositories.base import Session
from everest.repositories.base import SessionFactory
from everest.repositories.state import EntityState
from everest.traversal import SourceTargetDataTreeTraverser
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session as SaSession
from zope.sqlalchemy import ZopeTransactionExtension # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['RdbAutocommittingSession',
           'RdbSession',
           'RdbSessionFactory',
           'ScopedSessionMaker',
           ]


class RdbSession(Session, SaSession):
    """
    Special session class adapting the SQLAlchemy session for everest.
    """
    IS_MANAGING_BACKREFERENCES = False

    def __init__(self, *args, **options):
        self.__repository = options.pop('repository')
        SaSession.__init__(self, *args, **options)

    def get_by_id(self, entity_class, id_key):
        try:
            ent = self.query(entity_class).get(id_key)
        except NoResultsException:
            ent = None
        return ent

    def get_by_slug(self, entity_class, slug):
        # We don't have an optimization for access by slug here; returning
        # `None` indicates that a query should be run.
        return None

    def add(self, entity_class, data):
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
        return self.__run_traversal(entity_class, data, target,
                                    RELATION_OPERATIONS.UPDATE)

    def query(self, *entities, **options):
        # When called by everest from an aggregate, we use the default query
        # class that attempts to fetch the total result count and the first
        # result page in one call. For advanced custom queries, this feature
        # has to be disabled by using the default SA query class.
        # FIXME: Not intuitive. Also, we need a test case for this.
        query_cls = options.pop('query_class', None)
        if not query_cls is None:
            qry = query_cls(entities, self, **options) # pragma: no cover
        else:
            qry = self._query_cls(entities, self, **options)
        return qry

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

    def __call__(self, **kw):
        if not self.__fac.registry.has():
            self.__fac.configure(autoflush=self._repository.autoflush,
                                 query_cls=self.__query_class,
                                 repository=self._repository)
            if not self._repository.autocommit \
               and self._repository.join_transaction:
                # Enable the Zope transaction extension with the standard
                # sqlalchemy Session class.
                self.__fac.configure(extension=ZopeTransactionExtension())
        return self.__fac(**kw)
