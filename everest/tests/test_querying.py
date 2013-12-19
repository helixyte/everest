"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2012.
"""
from everest.entities.utils import get_root_aggregate
from everest.exceptions import MultipleResultsException
from everest.exceptions import NoResultsException
from everest.querying.base import CqlExpressionList
from everest.querying.filtering import CqlFilterExpression
from everest.querying.operators import ASCENDING
from everest.querying.operators import DESCENDING
from everest.querying.operators import GREATER_OR_EQUALS
from everest.querying.operators import GREATER_THAN
from everest.querying.operators import LESS_OR_EQUALS
from everest.querying.operators import LESS_THAN
from everest.querying.specifications import AscendingOrderSpecification
from everest.querying.specifications import DescendingOrderSpecification
from everest.querying.specifications import ValueEqualToFilterSpecification
from everest.repositories.memory.querying import EvalFilterExpression
from everest.repositories.memory.querying import EvalOrderExpression
from everest.repositories.rdb.testing import RdbTestCaseMixin
from everest.resources.staging import StagingAggregate
from everest.testing import EntityTestCase
from everest.testing import Pep8CompliantTestCase
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.interfaces import IMyEntity
from everest.tests.complete_app.testing import create_entity
from operator import and_ as operator_and
from operator import or_ as operator_or

__docformat__ = 'reStructuredText en'
__all__ = ['CqlExpressionTestCase',
           'EvalExpressionTestCase',
           'MemoryQueryTestCase',
           'MemoryRepositoryQueryTestCase',
           'RdbSessionQueryTestCase',
           ]


class CqlExpressionTestCase(Pep8CompliantTestCase):
    def test_cql_expression_combination(self):
        cql_expr = CqlFilterExpression('foo', LESS_THAN.name, '1')
        expr_str = 'foo:less-than:1'
        self.assert_equal(str(cql_expr), expr_str)
        cql_exprs = CqlExpressionList([cql_expr])
        and_expr_str = '~'.join((expr_str, expr_str))
        self.assert_equal(str(operator_and(cql_expr, cql_expr)),
                          and_expr_str)
        self.assert_equal(str(operator_and(cql_expr, cql_exprs)),
                          and_expr_str)
        self.assert_raises(TypeError, operator_and, cql_expr, None)
        self.assert_equal(str(operator_and(cql_exprs, cql_expr)),
                          and_expr_str)
        self.assert_equal(str(operator_and(cql_exprs, cql_exprs)),
                          and_expr_str)
        self.assert_raises(TypeError, operator_and, cql_exprs, None)
        cql_or_expr = operator_or(cql_expr, cql_expr)
        self.assert_equal(str(cql_or_expr), "%s,1" % expr_str)
        self.assert_raises(ValueError, operator_or, cql_expr,
                           CqlFilterExpression('bar', GREATER_THAN.name, '1'))

    def test_cql_expression_negation(self):
        inv_expr = ~CqlFilterExpression('foo', LESS_THAN.name, '1')
        self.assert_equal(inv_expr.op_name, GREATER_OR_EQUALS.name)
        inv_inv_expr = ~inv_expr
        self.assert_equal(inv_inv_expr.op_name, LESS_THAN.name)
        inv_expr = ~CqlFilterExpression('foo', GREATER_THAN.name, '1')
        self.assert_equal(inv_expr.op_name, LESS_OR_EQUALS.name)
        inv_inv_expr = ~inv_expr
        self.assert_equal(inv_inv_expr.op_name, GREATER_THAN.name)
        invalid_expr = CqlFilterExpression('foo', 'bar', '1')
        self.assert_raises(ValueError, invalid_expr.__invert__)


class EvalExpressionTestCase(Pep8CompliantTestCase):
    def test_filter_expr(self):
        expr0 = EvalFilterExpression(ValueEqualToFilterSpecification('id', 0))
        expr1 = \
         EvalFilterExpression(ValueEqualToFilterSpecification('text', 'text'))
        and_expr = expr0 & expr1
        or_expr = expr0 | expr1
        not_expr = ~expr0
        ent0 = MyEntity(id=0, text='text')
        ent1 = MyEntity(id=1, text='text')
        ents = [ent0, ent1]
        self.assert_equal(list(and_expr(ents)), [ent0])
        self.assert_equal(set(or_expr(ents)), set([ent0, ent1]))
        self.assert_equal(list(not_expr(ents)), [ent1])


class _BaseQueryTestCase(EntityTestCase):
    package_name = 'everest.tests.complete_app'

    def set_up(self):
        EntityTestCase.set_up(self)
        self._ent0 = create_entity(entity_id=0, entity_text='foo0')
        self._ent1 = create_entity(entity_id=1, entity_text='foo1')
        self._aggregate = get_root_aggregate(IMyEntity)
        self._aggregate.add(self._ent0)
        self._aggregate.add(self._ent1)

    @property
    def _query(self):
        return self._aggregate.query()

    def test_basics(self):
        self.assert_equal(set(self._query.all()),
                          set([self._ent0, self._ent1]))
        self.assert_equal(len(list(self._query)), 2)
        self.assert_equal(self._query.count(), 2)
        self.assert_equal(len(list(self._query.slice(0, 1))), 1)
        self.assert_equal(self._query.slice(0, 1).count(), 2)

    def test_one(self):
        self.assert_true(self._query.filter_by(id=1).one() is self._ent1)
        self.assert_raises(MultipleResultsException, self._query.one)
        self.assert_raises(NoResultsException,
                           self._query.filter_by(id=-1).one)

    def test_filter(self):
        q = self._query.filter_by(id=1).filter_by(text='foo1')
        self.assert_true(q.one() is self._ent1)

    def test_order_by(self):
        ent2 = create_entity(entity_id=2, entity_text='foo3')
        ent3 = create_entity(entity_id=3, entity_text='foo3')
        self._aggregate.add(ent2)
        self._aggregate.add(ent3)
        q = self._query.order_by(('text', ASCENDING), ('id', DESCENDING))
        last_ent = q.all()[-1]
        self.assert_true(last_ent is ent2)
        self.assert_raises(ValueError, self._query.order_by, ('text', None))

    def _test_order(self, txt_expr, id_expr):
        ent2 = create_entity(entity_id=2, entity_text='foo3')
        ent3 = create_entity(entity_id=3, entity_text='foo3')
        self._aggregate.add(ent2)
        self._aggregate.add(ent3)
        q = self._query.order(txt_expr)
        self.assert_true(next(iter(q)) is self._ent0)
        q = q.order(None)
        q = q.order(txt_expr).order(id_expr)
        last_ent = q.all()[-1]
        self.assert_true(last_ent is ent2)


class MemoryRepositoryQueryTestCase(_BaseQueryTestCase):
    config_file_name = 'configure_no_rdb.zcml'

    def test_order(self):
        txt_spec = AscendingOrderSpecification('text')
        txt_expr = EvalOrderExpression(txt_spec)
        id_spec = DescendingOrderSpecification('id')
        id_expr = EvalOrderExpression(id_spec)
        self._test_order(txt_expr, id_expr)


class RdbSessionQueryTestCase(RdbTestCaseMixin, _BaseQueryTestCase):
    def test_order(self):
        txt_expr = MyEntity.text.asc()
        id_expr = MyEntity.id.desc()
        self._test_order(txt_expr, id_expr)


class MemoryQueryTestCase(EntityTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def test_basics(self):
        agg = StagingAggregate(MyEntity)
        ent0 = MyEntity(id=0, text='text0')
        ent1 = MyEntity(id=1, text='text1')
        agg.add(ent0)
        agg.add(ent1)
        q = agg.query()
        filter_expr = \
            EvalFilterExpression(ValueEqualToFilterSpecification('id', 0))
        self.assert_equal(q.filter(filter_expr).all(), [ent0])
        self.assert_equal(len(q.slice(1, 2).all()), 1)
        self.assert_equal(q.slice(1, 2).count(), 2)
        order_expr = EvalOrderExpression(AscendingOrderSpecification('text'))
        q = q.order(order_expr)
        self.assert_equal(q.all()[0].text, 'text0')
