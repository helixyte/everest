"""
Testing utilities for the noSQL backend.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 26, 2013.
"""
from everest.repositories.nosqldb.utils import MongoClassRegistry

__docformat__ = 'reStructuredText en'
__all__ = ['NoSqlTestCaseMixin',
           ]


class NoSqlTestCaseMixin(object):
    """
    Mixin for test cases using the NoSQL backend.

    Ensures that all classes instrumented to work with Mongo DB are
    unregistered on class teardown.
    """
    @classmethod
    def teardown_class(cls):
        MongoClassRegistry.unregister_all()
        base_cls = super(NoSqlTestCaseMixin, cls)
        try:
            base_cls.teardown_class()
        except AttributeError:
            pass
