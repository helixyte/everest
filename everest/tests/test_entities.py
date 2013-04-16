"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2012.
"""
from everest.entities.base import Entity
from everest.testing import Pep8CompliantTestCase

__docformat__ = 'reStructuredText en'
__all__ = ['EntitiesTestCase',
           ]


class EntitiesTestCase(Pep8CompliantTestCase):
    def test_base(self):
        ent00 = MyEntity(id=0)
        ent01 = MyEntity(id=0)
        ent1 = MyEntity(id=1)
        self.assert_equal(ent00, ent01)
        self.assert_not_equal(ent00, ent1)


class MyEntity(Entity):
    pass
