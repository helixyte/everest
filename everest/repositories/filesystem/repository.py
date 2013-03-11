"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from everest.mime import CsvMime
from everest.repositories.memory.repository import MemoryRepository
from everest.repositories.memory.repository import MemorySessionFactory
from everest.resources.io import dump_resource
from everest.resources.io import get_read_collection_path
from everest.resources.io import get_write_collection_path
from everest.resources.io import load_collection_from_url
from everest.resources.staging import create_staging_collection
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_member_class
import os

__all__ = ['FileSystemRepository',
           ]


class FileSystemRepository(MemoryRepository):
    """
    Repository using the file system as storage.
    
    On initialization, this repository loads resource representations from
    files into the root repository. Each commit operation writes the specified
    resource back to file.
    """
    _configurables = MemoryRepository._configurables \
                     + ['directory', 'content_type']

    def __init__(self, name, aggregate_class=None,
                 join_transaction=True, autocommit=False):
        MemoryRepository.__init__(self, name,
                                  aggregate_class=aggregate_class,
                                  join_transaction=join_transaction,
                                  autocommit=autocommit)
        self.configure(directory=os.getcwd(), content_type=CsvMime,
                       cache_loader=self.__load_entities)

    def commit(self, unit_of_work):
        """
        Dump all resources that were modified by the given session back into
        the repository.
        """
        MemoryRepository.commit(self, unit_of_work)
        if self.is_initialized:
            entity_classes_to_dump = set()
            for info in unit_of_work.iterator():
                entity_classes_to_dump.add(info[0])
            for entity_cls in entity_classes_to_dump:
                self.__dump_entities(entity_cls)

    def _make_session_factory(self):
        return MemorySessionFactory(self)

    def __load_entities(self, entity_class):
        coll_cls = get_collection_class(entity_class)
        fn = get_read_collection_path(coll_cls, self._config['content_type'],
                                      directory=self._config['directory'])
        if not fn is None:
            url = 'file://%s' % fn
            coll = load_collection_from_url(coll_cls, url,
                                            content_type=
                                                self._config['content_type'])
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
        coll = create_staging_collection(coll_cls)
        for ent in cache.iterator():
            coll.add(mb_cls.create_from_entity(ent))
        # Open stream for writing and dump the collection.
        stream = file(fn, 'w')
        with stream:
            dump_resource(coll, stream,
                          content_type=self._config['content_type'])
