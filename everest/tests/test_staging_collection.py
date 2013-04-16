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

    def test_basics(self):
        foo = FooEntity(id=0)
        foo_mb = FooMember.create_from_entity(foo)
        self.coll.add(foo_mb)
        agg = self.coll.get_aggregate()
        self.assert_true(agg.get_by_id(foo.id) is foo)
        self.assert_true(agg.get_by_slug(foo.slug) is foo)
        foo1 = FooEntity(id=0)
        txt = 'FROBNIC'
        foo1.text = txt
        agg.update(foo1)
        self.assert_equal(agg.get_by_id(foo.id).text, txt)
        self.assert_equal(len(list(agg.iterator())), 1)
        agg.remove(foo)
        self.assert_equal(len(list(agg.iterator())), 0)
