"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 10, 2011.
"""
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.scoping import scoped_session
from sqlalchemy.orm.session import sessionmaker

from everest.querying.filtering import CqlFilterSpecificationVisitor
from everest.querying.ordering import CqlOrderSpecificationVisitor
from everest.querying.specifications import FilterSpecificationFactory
from everest.querying.specifications import OrderSpecificationFactory
from everest.repositories.rdb import SqlFilterSpecificationVisitor
from everest.repositories.rdb import SqlOrderSpecificationVisitor
from everest.repositories.rdb.querying import OrderClauseList
from everest.repositories.rdb.utils import reset_metadata
from everest.testing import Pep8CompliantTestCase
import sqlalchemy as sa
import sqlalchemy.orm as orm


__docformat__ = 'reStructuredText en'
__all__ = ['CqlFilterSpecificationVisitorTestCase',
           'CqlOrderSpecificationVisitorTestCase',
           'SqlFilterSpecificationVisitorTestCase',
           'SqlOrderSpecificationVisitorTestCase',
           ]


class Person(object):
    metadata = None
    id = None
    name = None
    age = None

    def __init__(self, name, age):
        self.name = name
        self.age = age


def create_metadata(engine):
    metadata = sa.MetaData()
    person_table = sa.Table('person', metadata,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String, nullable=False, unique=True),
        sa.Column('age', sa.Integer, nullable=False),
        )
    orm.mapper(Person, person_table)
    metadata.bind = engine
    metadata.create_all()
    return metadata


def teardown():
    # Module level tear down.
    if not Person.metadata is None:
        Person.metadata.drop_all()
        Person.metadata = None
    reset_metadata()


class VisitorTestCase(Pep8CompliantTestCase):
    visitor = None
    specs_factory = None
    _spec_map = None

    def set_up(self):
        Pep8CompliantTestCase.set_up(self)
        self.visitor = self._make_visitor()
        self.specs_factory = self._make_specs_factory()

    def _get_spec(self, name):
        return self._get_spec_map()[name]

    def _get_spec_map(self):
        if self._spec_map is None:
            self._spec_map = self._init_spec_map()
        return self._spec_map

    def _run_visitor(self, spec_name):
        spec = self._get_spec(spec_name)
        spec.accept(self.visitor)
        return self.visitor.expression

    def _make_visitor(self):
        raise NotImplementedError('Abstract method.')

    def _make_specs_factory(self):
        raise NotImplementedError('Abstract method.')

    def _init_spec_map(self):
        raise NotImplementedError('Abstract method.')


class FilterVisitorTestCase(VisitorTestCase):

    def _make_visitor(self):
        raise NotImplementedError('Abstract method.')

    def _make_specs_factory(self):
        return FilterSpecificationFactory()

    def _init_spec_map(self):
        sm = {}
        sm['starts-with'] = \
            self.specs_factory.create_starts_with('name', 'Ni')
        sm['ends-with'] = \
            self.specs_factory.create_ends_with('name', 'os')
        sm['contains'] = \
            self.specs_factory.create_contains('name', 'iko')
        sm['contained'] = \
            self.specs_factory.create_contained('age', [22, 33, 44, 55])
        sm['equal-to'] = \
            self.specs_factory.create_equal_to('name', 'Nikos')
        sm['less-than'] = \
            self.specs_factory.create_less_than('age', 34)
        sm['less-than-or-equal-to'] = \
            self.specs_factory.create_less_than_or_equal_to('age', 34)
        sm['greater-than'] = \
            self.specs_factory.create_greater_than('age', 34)
        sm['greater-than-or-equal-to'] = \
            self.specs_factory.create_greater_than_or_equal_to('age', 34)
        sm['in-range'] = \
            self.specs_factory.create_in_range('age', (30, 40))
        left_spec = self.specs_factory.create_greater_than('age', 34)
        right_spec = self.specs_factory.create_equal_to('name', 'Nikos')
        sm['conjunction'] = left_spec & right_spec
        spec1 = self.specs_factory.create_equal_to('age', 34)
        spec2 = self.specs_factory.create_equal_to('age', 44)
        sm['disjunction'] = spec1 | spec2
        spec_a1 = self.specs_factory.create_equal_to('age', 34)
        spec_a2 = self.specs_factory.create_equal_to('age', 44)
        spec_a = spec_a1 | spec_a2
        spec_b1 = self.specs_factory.create_equal_to('name', 'Nikos')
        spec_b2 = self.specs_factory.create_equal_to('name', 'Oliver')
        spec_b = spec_b1 | spec_b2
        sm['conjunction-with-disjunction'] = spec_a & spec_b
        sm['not-starts-with'] = ~sm['starts-with']
        sm['not-ends-with'] = ~sm['ends-with']
        sm['not-contains'] = ~sm['contains']
        sm['not-contained'] = ~sm['contained']
        sm['not-equal-to'] = ~sm['equal-to']
        sm['not-less-than'] = ~sm['less-than']
        sm['not-less-than-or-equal-to'] = ~sm['less-than-or-equal-to']
        sm['not-greater-than'] = ~sm['greater-than']
        sm['not-greater-than-or-equal-to'] = ~sm['greater-than-or-equal-to']
        sm['not-in-range'] = ~sm['in-range']
        return sm


class CqlFilterSpecificationVisitorTestCase(FilterVisitorTestCase):

    def _make_visitor(self):
        return CqlFilterSpecificationVisitor()

    def test_visit_value_starts_with(self):
        expected_cql = 'name:starts-with:"Ni"'
        expr = self._run_visitor('starts-with')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_ends_with(self):
        expected_cql = 'name:ends-with:"os"'
        expr = self._run_visitor('ends-with')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_contains(self):
        expected_cql = 'name:contains:"iko"'
        expr = self._run_visitor('contains')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_contained(self):
        expected_cql = 'age:contained:22,33,44,55'
        expr = self._run_visitor('contained')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_equal_to(self):
        expected_cql = 'name:equal-to:"Nikos"'
        expr = self._run_visitor('equal-to')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_less_than(self):
        expected_cql = 'age:less-than:34'
        expr = self._run_visitor('less-than')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_less_or_equals(self):
        expected_cql = 'age:less-than-or-equal-to:34'
        expr = self._run_visitor('less-than-or-equal-to')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_greater_than(self):
        expected_cql = 'age:greater-than:34'
        expr = self._run_visitor('greater-than')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_greater_or_equals(self):
        expected_cql = 'age:greater-than-or-equal-to:34'
        expr = self._run_visitor('greater-than-or-equal-to')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_in_range(self):
        expected_cql = 'age:in-range:30-40'
        expr = self._run_visitor('in-range')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_Conjunction(self):
        expected_cql = 'age:greater-than:34~name:equal-to:"Nikos"'
        expr = self._run_visitor('conjunction')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_disjuction(self):
        expected_cql = 'age:equal-to:34,44'
        expr = self._run_visitor('disjunction')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_Conjunction_with_disjuction(self):
        expected_cql = 'age:equal-to:34,44~name:equal-to:"Nikos","Oliver"'
        expr = self._run_visitor('conjunction-with-disjunction')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_not_starts_with(self):
        expected_cql = 'name:not-starts-with:"Ni"'
        expr = self._run_visitor('not-starts-with')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_not_ends_with(self):
        expected_cql = 'name:not-ends-with:"os"'
        expr = self._run_visitor('not-ends-with')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_not_contains(self):
        expected_cql = 'name:not-contains:"iko"'
        expr = self._run_visitor('not-contains')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_not_equal_to_many(self):
        expected_cql = 'age:not-contained:22,33,44,55'
        expr = self._run_visitor('not-contained')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_not_equal_to(self):
        expected_cql = 'name:not-equal-to:"Nikos"'
        expr = self._run_visitor('not-equal-to')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_not_less_than(self):
        expected_cql = 'age:greater-than-or-equal-to:34'
        expr = self._run_visitor('not-less-than')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_not_less_or_equals(self):
        expected_cql = 'age:greater-than:34'
        expr = self._run_visitor('not-less-than-or-equal-to')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_not_greater_than(self):
        expected_cql = 'age:less-than-or-equal-to:34'
        expr = self._run_visitor('not-greater-than')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_not_greater_or_equals(self):
        expected_cql = 'age:less-than:34'
        expr = self._run_visitor('not-greater-than-or-equal-to')
        self.assert_equal(str(expr), expected_cql)

    def test_visit_value_not_in_range(self):
        expected_cql = 'age:not-in-range:30-40'
        expr = self._run_visitor('not-in-range')
        self.assert_equal(str(expr), expected_cql)


class SqlFilterSpecificationVisitorTestCase(FilterVisitorTestCase):
    def set_up(self):
        if Person.metadata is None:
            reset_metadata()
            engine = create_engine('sqlite://')
            metadata = create_metadata(engine)
            Person.metadata = metadata
            metadata.bind = engine
        VisitorTestCase.set_up(self)

    def _make_visitor(self):
        return SqlFilterSpecificationVisitor(Person)

    def test_visit_value_starts_with(self):
        expected_expr = Person.name.startswith('Ni')
        expr = self._run_visitor('starts-with')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_value_ends_with(self):
        expected_expr = Person.name.endswith('os')
        expr = self._run_visitor('ends-with')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_value_contains(self):
        expected_expr = Person.name.contains('iko')
        expr = self._run_visitor('contains')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_value_contained(self):
        expected_expr = Person.age.in_([22, 33, 44, 55])
        expr = self._run_visitor('contained')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_value_equal_to(self):
        expected_expr = Person.name == 'Nikos'
        expr = self._run_visitor('equal-to')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_value_less_than(self):
        expected_expr = Person.age < 34
        expr = self._run_visitor('less-than')
        self.assert_equal(str(expr), str(expected_expr))

    def _test_visit_value_less_or_equals(self):
        expected_expr = Person.age <= 34
        expr = self._run_visitor('less-than-or-equal-to')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_value_greater_than(self):
        expected_expr = Person.age > 34
        expr = self._run_visitor('greater-than')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_value_greater_or_equals(self):
        expected_expr = Person.age >= 34
        expr = self._run_visitor('greater-than-or-equal-to')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_value_in_range(self):
        expected_expr = Person.age.between(30, 40)
        expr = self._run_visitor('in-range')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_Conjunction(self):
        expected_expr = sa.and_(Person.age > 34, Person.name == 'Nikos')
        expr = self._run_visitor('conjunction')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_disjuction(self):
        expected_expr = sa.or_(Person.age == 34, Person.age == 44)
        expr = self._run_visitor('disjunction')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_Conjunction_with_list_equality(self):
        expected_expr = sa.and_(Person.age.in_([34, 44]),
                                Person.name.in_(['Nikos', 'Oliver']))
        spec_a = self.specs_factory.create_contained('age', [34, 44])
        spec_b = self.specs_factory.create_contained('name',
                                                     ['Nikos', 'Oliver'])
        spec = spec_a & spec_b
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.expression),
                          str(expected_expr))

    def test_visit_value_not_starts_with(self):
        expected_expr = sa.not_(Person.name.startswith('Ni'))
        expr = self._run_visitor('not-starts-with')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_value_not_ends_with(self):
        expected_expr = sa.not_(Person.name.endswith('os'))
        expr = self._run_visitor('not-ends-with')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_value_not_contains(self):
        expected_expr = sa.not_(Person.name.contains('iko'))
        expr = self._run_visitor('not-contains')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_value_not_equal_to(self):
        expected_expr = sa.not_(Person.name == 'Nikos')
        expr = self._run_visitor('not-equal-to')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_value_not_less_than(self):
        expected_expr = sa.not_(Person.age < 34)
        expr = self._run_visitor('not-less-than')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_value_not_less_or_equals(self):
        expected_expr = sa.not_(Person.age <= 34)
        expr = self._run_visitor('not-less-than-or-equal-to')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_value_not_greater_than(self):
        expected_expr = sa.not_(Person.age > 34)
        expr = self._run_visitor('not-greater-than')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_value_not_greater_or_equals(self):
        expected_expr = sa.not_(Person.age >= 34)
        expr = self._run_visitor('not-greater-than-or-equal-to')
        self.assert_equal(str(expr), str(expected_expr))

    def test_visit_value_not_in_range(self):
        expected_expr = sa.not_(Person.age.between(30, 40))
        expr = self._run_visitor('not-in-range')
        self.assert_equal(str(expr), str(expected_expr))


class OrderVisitorTestCase(VisitorTestCase):

    def _make_visitor(self):
        raise NotImplementedError('Abstract method.')

    def _make_specs_factory(self):
        return OrderSpecificationFactory()

    def _init_spec_map(self):
        sm = {}
        sm['one-asc'] = self.specs_factory.create_ascending('name')
        sm['one-desc'] = self.specs_factory.create_descending('name')
        sm['two-asc-asc'] = self.specs_factory.create_ascending('name') \
                            & self.specs_factory.create_ascending('age')
        sm['two-desc-asc'] = self.specs_factory.create_descending('name') \
                             & self.specs_factory.create_ascending('age')
        sm['two-asc-desc'] = self.specs_factory.create_ascending('name') \
                             & self.specs_factory.create_descending('age')
        sm['two-desc-desc'] = self.specs_factory.create_descending('name') \
                              & self.specs_factory.create_descending('age')
        return sm


class SqlOrderSpecificationVisitorTestCase(OrderVisitorTestCase):

    def _make_visitor(self):
        return SqlOrderSpecificationVisitor(Person)

    def set_up(self):
        if Person.metadata is None:
            engine = create_engine('sqlite://')
            Person.metadata = create_metadata(engine)
        OrderVisitorTestCase.set_up(self)

    def test_simple_order_by_one_attribute(self):
        expected_expr = Person.name.asc()
        expr = self._run_visitor('one-asc')
        self.assert_equal(str(expr), str(expected_expr))

    def test_simple_reversed_order_by_one_attribute(self):
        expected_expr = Person.name.desc()
        expr = self._run_visitor('one-desc')
        self.assert_equal(str(expr), str(expected_expr))

    def test_simple_order_by_two_attributes(self):
        expected_expr = OrderClauseList(Person.name.asc(), Person.age.asc())
        expr = self._run_visitor('two-asc-asc')
        self.assert_equal(str(expr), str(expected_expr))

    def test_simple_order_by_two_attributes_left_reversed(self):
        expected_expr = OrderClauseList(Person.name.desc(), Person.age.asc())
        expr = self._run_visitor('two-desc-asc')
        self.assert_equal(str(expr), str(expected_expr))

    def test_simple_order_by_two_attributes_right_reversed(self):
        expected_expr = OrderClauseList(Person.name.asc(), Person.age.desc())
        expr = self._run_visitor('two-asc-desc')
        self.assert_equal(str(expr), str(expected_expr))

    def test_simple_order_by_two_attributes_both_reversed(self):
        expected_expr = OrderClauseList(Person.name.desc(), Person.age.desc())
        expr = self._run_visitor('two-desc-desc')
        self.assert_equal(str(expr), str(expected_expr))

    def test_order_clause_list(self):
        # This emulates customized comparators which return clause lists
        # for .asc and .desc operations.
        old_asc = Person.name.asc
        expected_expr = OrderClauseList(Person.id.asc(),
                                        Person.name.asc(),
                                        Person.age.asc())
        self.assert_equal(str(expected_expr),
                          'person.id ASC, person.name ASC, person.age ASC')
        try:
            Person.name.asc = lambda : OrderClauseList(Person.id.asc(),
                                                       old_asc())
            expr = self._run_visitor('two-asc-asc')
            self.assert_equal(str(expr), str(expected_expr))
        finally:
            Person.name.asc = old_asc
        # Make sure the correct ORDER BY clause is generated.
        sm = scoped_session(sessionmaker())
        sess = sm()
        q = sess.query(Person).order_by(expr) # pylint: disable=E1101
        q_str = str(q.statement)
        self.assert_not_equal(q_str.find("ORDER BY %s" % expr), -1)


class CqlOrderSpecificationVisitorTestCase(OrderVisitorTestCase):
    visitor = None
    order_factory = None

    def _make_visitor(self):
        return CqlOrderSpecificationVisitor()

    def test_simple_order_by_one_attribute(self):
        expected_cql = 'name:asc'
        expr = self._run_visitor('one-asc')
        self.assert_equal(str(expr), expected_cql)

    def test_simple_reversed_order_by_one_attribute(self):
        expected_cql = 'name:desc'
        expr = self._run_visitor('one-desc')
        self.assert_equal(str(expr), expected_cql)

    def test_simple_order_by_two_attributes(self):
        expected_cql = 'name:asc~age:asc'
        expr = self._run_visitor('two-asc-asc')
        self.assert_equal(str(expr), expected_cql)

    def test_simple_order_by_two_attributes_left_reversed(self):
        expected_cql = 'name:desc~age:asc'
        expr = self._run_visitor('two-desc-asc')
        self.assert_equal(str(expr), expected_cql)

    def test_simple_order_by_two_attributes_right_reversed(self):
        expected_cql = 'name:asc~age:desc'
        expr = self._run_visitor('two-asc-desc')
        self.assert_equal(str(expr), expected_cql)

    def test_simple_order_by_two_attributes_both_reversed(self):
        expected_cql = 'name:desc~age:desc'
        expr = self._run_visitor('two-desc-desc')
        self.assert_equal(str(expr), expected_cql)
