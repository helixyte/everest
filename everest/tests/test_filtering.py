"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 5, 2011.
"""
from everest.repositories.rdb import SqlFilterSpecificationVisitor
from everest.querying.specifications import ValueEqualToFilterSpecification
from everest.testing import Pep8CompliantTestCase
from everest.tests.simple_app.entities import FooEntity

__docformat__ = 'reStructuredText en'
__all__ = ['SqlFilterSpecificationVisitorTestCase',
           ]


class SqlFilterSpecificationVisitorTestCase(Pep8CompliantTestCase):
    def test_custom_clause(self):
        obj = object()
        func = lambda value: obj
        spec = ValueEqualToFilterSpecification('foo', 'bar')
        factory_map = {('foo', spec.operator.name):func}
        visitor = SqlFilterSpecificationVisitor(FooEntity,
                                                custom_clause_factories=
                                                                 factory_map)
        visitor.visit_nullary(spec)
        self.assert_true(visitor.expression is obj)
