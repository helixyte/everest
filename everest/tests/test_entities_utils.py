"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2012.
"""
from everest.repositories.memory import Aggregate
from everest.entities.utils import get_entity_class
from everest.entities.utils import get_root_aggregate
from everest.entities.utils import identifier_from_slug
from everest.entities.utils import slug_from_identifier
from everest.entities.utils import slug_from_integer
from everest.entities.utils import slug_from_string
from everest.testing import EntityTestCase
from everest.tests.simple_app.entities import FooEntity
from everest.tests.simple_app.interfaces import IFoo

__docformat__ = 'reStructuredText en'
__all__ = ['EntitiesUtilsTestCase',
           ]


class EntitiesUtilsTestCase(EntityTestCase):
    package_name = 'everest.tests.simple_app'

    def test_get_root_aggregate(self):
        agg = get_root_aggregate(IFoo)
        self.assert_true(isinstance(agg, Aggregate))

    def test_get_entity_class(self):
        self.assert_true(get_entity_class(IFoo), FooEntity)

    def test_get_slug_from_string(self):
        self.assert_equal(slug_from_string('a b_C'), 'a-b-c')

    def test_get_slug_from_integer(self):
        self.assert_equal(slug_from_integer(1), '1')

    def test_get_slug_from_identifier(self):
        self.assert_equal(slug_from_identifier('a_b'), 'a-b')

    def test_get_identifier_from_slug(self):
        self.assert_equal(identifier_from_slug('a-b'), 'a_b')
