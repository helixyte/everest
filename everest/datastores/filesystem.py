"""
File system data store.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 5, 2013.
"""
from everest.datastores.memory import InMemoryDataStore
from everest.datastores.memory import InMemorySessionFactory
from everest.mime import CsvMime
from everest.resources.io import dump_resource
from everest.resources.io import get_read_collection_path
from everest.resources.io import get_write_collection_path
from everest.resources.io import load_collection_from_url
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_member_class
from everest.resources.utils import new_stage_collection
import os

__docformat__ = 'reStructuredText en'
__all__ = ['FileSystemDataStore',
           ]


class FileSystemDataStore(InMemoryDataStore):
    """
    Data store using the file system as storage.
    
    On initialization, this entity store loads resource representations from
    files into the root repository. Each commit operation writes the specified
    resource back to file.
    """
    _configurables = InMemoryDataStore._configurables \
                     + ['directory', 'content_type']

    def __init__(self, name,
                 autoflush=True, join_transaction=True, autocommit=False):
        InMemoryDataStore.__init__(self, name, autoflush=autoflush,
                                    join_transaction=join_transaction,
                                    autocommit=autocommit)
        self.configure(directory=os.getcwd(), content_type=CsvMime,
                       cache_loader=self.__load_entities)

    def commit(self, session):
        """
        Dump all resources that were modified by the given session back into
        the store.
        """
        with self._cache_lock:
            InMemoryDataStore.commit(self, session)
            if self.is_initialized:
                for entity_cls in session.dirty.keys():
                    self.__dump_entities(entity_cls)

    def _make_session_factory(self):
        return InMemorySessionFactory(self)

    def __load_entities(self, entity_class):
        coll_cls = get_collection_class(entity_class)
        fn = get_read_collection_path(coll_cls, self._config['content_type'],
                                      directory=self._config['directory'])
        if not fn is None:
            url = 'file://%s' % fn
            coll = load_collection_from_url(coll_cls, url,
                                            content_type=
                                                self._config['content_type'],
                                            resolve_urls=False)
            ents = [mb.get_entity() for mb in coll]
        else:
            ents = []
        return ents

    def __dump_entities(self, entity_class):
        cache = self._get_cache(entity_class)
        coll_cls = get_collection_class(entity_class)
        mb_cls = get_member_class(entity_class)
        fn = get_write_collection_path(coll_cls,
                                       self._config['content_type'],
                                       directory=self._config['directory'])
        # Wrap the entities in a temporary collection.
        coll = new_stage_collection(coll_cls)
        for ent in cache.get_all():
            coll.add(mb_cls.create_from_entity(ent))
        # Open stream for writing and dump the collection.
        stream = file(fn, 'w')
        with stream:
            dump_resource(coll, stream,
                          content_type=self._config['content_type'])
