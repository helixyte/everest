"""
Repository for the relational database (rdb) backend.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from sqlalchemy.engine import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import StaticPool

from everest.repositories.base import Repository
from everest.repositories.rdb.aggregate import RdbAggregate
from everest.repositories.rdb.querying import OptimizedCountingQuery
from everest.repositories.rdb.querying import SimpleCountingQuery
from everest.repositories.rdb.session import RdbSessionFactory
from everest.repositories.rdb.utils import empty_metadata
from everest.repositories.rdb.utils import get_metadata
from everest.repositories.rdb.utils import is_metadata_initialized
from everest.repositories.rdb.utils import map_system_entities
from everest.repositories.rdb.utils import reset_metadata
from everest.repositories.rdb.utils import set_metadata
from everest.repositories.utils import get_engine
from everest.repositories.utils import is_engine_initialized
from everest.repositories.utils import set_engine


__docformat__ = 'reStructuredText en'
__all__ = ['RdbRepository',
           ]


class RdbRepository(Repository):
    """
    Repository connected to a relational database backend (through an ORM).
    """
    _configurables = Repository._configurables \
                     + ['db_string', 'metadata_factory']

    def __init__(self, name, aggregate_class=None,
                 autoflush=True, join_transaction=True, autocommit=False):
        """
        :param autoflush: Sets the `autoflush` attribute.
        """
        if aggregate_class is None:
            aggregate_class = RdbAggregate
        Repository.__init__(self, name, aggregate_class,
                            join_transaction=join_transaction,
                            autocommit=autocommit)
        #: Flag indicating if changes should be flushed to the treansaction
        #: automatically.
        self.autoflush = autoflush
        # Default to an in-memory sqlite DB.
        self.configure(db_string='sqlite://',
                       metadata_factory=empty_metadata)

    def _initialize(self):
        # Manages a RDB engine and a metadata instance for this repository.
        # Both are global objects that should only be created once per process
        # (for each RDB repository), hence we use a global object manager.
        if not is_engine_initialized(self.name):
            engine = self.__make_engine()
            set_engine(self.name, engine)
            # Bind the engine to the session factory and the metadata.
            self.session_factory.configure(bind=engine)
        else:
            engine = get_engine(self.name)
        if not is_metadata_initialized(self.name):
            md_fac = self._config['metadata_factory']
            if self._config.get('messaging_enable', False):
                # Wrap the metadata callback to also call the mapping
                # function for system entities.
                reset_on_start = \
                    self._config.get('messaging_reset_on_start', False)
                def wrapper(engine, reset_on_start=reset_on_start):
                    metadata = md_fac(engine)
                    map_system_entities(engine, metadata, reset_on_start)
                    return metadata
                metadata = wrapper(engine)
            else:
                metadata = md_fac(engine)
            set_metadata(self.name, metadata)
        else:
            metadata = get_metadata(self.name)
        metadata.bind = engine

    def _reset(self):
        # It is safe to keep the engine around, even for complex unit test
        # scenarios; the metadata, however, might change and need to be
        # removed.
        if is_metadata_initialized(self.name):
            reset_metadata()

    def _make_session_factory(self):
        engine = get_engine(self.name)
        query_class = self.__check_query_class(engine)
        return RdbSessionFactory(self, query_class)

    def __make_engine(self):
        db_string = self._config['db_string']
        if db_string.startswith('sqlite://'):
            # Enable connection sharing across threads for pysqlite.
            kw = {'poolclass':StaticPool,
                  'connect_args':{'check_same_thread':False}
                  }
        else:
            kw = {} # pragma: no cover
        return create_engine(db_string, **kw)

    def __check_query_class(self, engine):
        # We check if the backend supports windowing for optimized counting.
        conn = engine.connect()
        try:
            conn.execute("select count(1) over()")
        except OperationalError:
            query_class = SimpleCountingQuery
        else:
            query_class = OptimizedCountingQuery # pragma: no cover
        return query_class
