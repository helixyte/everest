"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 8, 2013.
"""
from everest.repositories.uow import UnitOfWork

__docformat__ = 'reStructuredText en'
__all__ = ['NoSqlSession',
           ]


class NoSqlSession(object):
    """
    Session object.
    """
    def __init__(self, repository):
        self.__repository = repository
        self.__unit_of_work = UnitOfWork()

    def commit(self):
        pass

    def rollback(self):
        pass

    def add(self, entity_class, entity):
        pass

    def remove(self, entity):
        pass

    def replace(self, entity):
        pass

    def get_by_id(self, entity_id):
        pass

    def get_by_slug(self, entity_slug):
        pass

    def iterator(self):
        pass

    def __make_class_key(self, entity_class):
        return "%s.%s" % (entity_class.__module__, entity_class.__name__)
