"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 14, 2012.
"""
from everest.resources.base import Collection
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_service
from everest.testing import ResourceTestCase
from everest.tests.complete_app.interfaces import IMyEntity
from zope.interface import Interface # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['ServiceTestCase',
           ]


class ServiceTestCase(ResourceTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def set_up(self):
        ResourceTestCase.set_up(self)
        self.srv = get_service()

    def test_register_after_start_raises_error(self):
        self.assert_raises(RuntimeError, self.srv.register, IFooResource)

    def test__getitem__(self):
        self.assert_true(isinstance(self.srv['my-entities'],
                                    get_collection_class(IMyEntity)))

    def test_remove(self):
        num_colls = len(self.srv)
        self.srv.remove(IMyEntity)
        self.assert_raises(KeyError, self.srv.__getitem__, 'my-entities')
        self.assert_equal(len(self.srv), num_colls - 1)

    def test__iter__(self):
        for coll in self.srv:
            self.assert_true(isinstance(coll, Collection))

    def test_add_with_existing_name_raises_error(self):
        self.assert_raises(ValueError, self.srv.add, IMyEntity)


class IFooResource(Interface): # pylint: disable=W0232
    pass
