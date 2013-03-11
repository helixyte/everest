"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Mar 10, 2013.
"""
from everest.resources.staging import create_staging_collection
from everest.testing import ResourceTestCase
from everest.tests.simple_app.entities import FooEntity
from everest.tests.simple_app.interfaces import IFoo
from everest.tests.simple_app.resources import FooMember


__docformat__ = 'reStructuredText en'
__all__ = ['StagingCollectionTestCase',
           ]


class StagingCollectionTestCase(ResourceTestCase):
    package_name = 'everest.tests.simple_app'

    def set_up(self):
        ResourceTestCase.set_up(self)
        self.coll = create_staging_collection(IFoo)
        self.session = self.coll.get_aggregate()._session # pylint:disable=W0212

    def test_basics(self):
        foo = FooEntity()
        foo_mb = FooMember.create_from_entity(foo)
        self.coll.add(foo_mb)
        self.assert_true(self.session.iterator(FooEntity).next() is foo)
        self.assert_equal(len(list(self.session.iterator(FooEntity))), 1)
