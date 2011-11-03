"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 11, 2011.
"""

from everest.resources.interfaces import IResource
from everest.specifications import ValueBoundSpecification
from everest.url import resource_to_url
from odict import odict
from sqlalchemy.sql import operators
import sqlalchemy

__docformat__ = 'reStructuredText en'
__all__ = ['FilterCqlGenerationVisitor',
           'QueryFilterGenerationVisitor',
           'SortOrderCqlGenerationVisitor',
           'SpecificationVisitor',
           ]


class SpecificationVisitor(object):
    """
    Abstract base class for all specification visitors
    """

    def __init__(self):
        if self.__class__ is SpecificationVisitor:
            raise NotImplementedError('Abstract class')

    def visit_conjuction(self, spec):
        """
        Visit a conjuction specification

        :param spec: a specification instance
        :type spec: :class:`everest.specifications.ConjuctionSpecification`
        """
        raise NotImplementedError('Abstract method')

    def visit_disjuction(self, spec):
        """
        Visit a disjuction specification

        :param spec: a specification instance
        :type spec: :class:`everest.specifications.DisjuctionSpecification`
        """
        raise NotImplementedError('Abstract method')

    def visit_negation(self, spec):
        """
        Visit a negation specification

        :param spec: a specification instance
        :type spec: :class:`everest.specifications.NegationSpecification`
        """
        raise NotImplementedError('Abstract method')

    def visit_value_starts_with(self, spec):
        """
        Visit a value starts with specification

        :param spec: a specification instance
        :type spec: :class:`everest.specifications.ValueStartsWithSpecification`
        """
        raise NotImplementedError('Abstract method')

    def visit_value_ends_with(self, spec):
        """
        Visit a value ends with specification

        :param spec: a specification instance
        :type spec: :class:`everest.specifications.ValueEndsWithSpecification`
        """
        raise NotImplementedError('Abstract method')

    def visit_value_contains(self, spec):
        """
        Visit a value contains specification

        :param spec: a specification instance
        :type spec: :class:`everest.specifications.ValueContainsSpecification`
        """
        raise NotImplementedError('Abstract method')

    def visit_value_contained(self, spec):
        """
        Visit a value contained specification

        :param spec: a specification instance
        :type spec: :class:`everest.specifications.ValueContainedSpecification`
        """
        raise NotImplementedError('Abstract method')

    def visit_value_equal_to(self, spec):
        """
        Visit a value equal to specification

        :param spec: a specification instance
        :type spec: :class:`everest.specifications.ValueEqualToSpecification`
        """
        raise NotImplementedError('Abstract method')

    def visit_value_less_than(self, spec):
        """
        Visit a value less than specification

        :param spec: a specification instance
        :type spec: :class:`everest.specifications.ValueLessThanSpecification`
        """
        raise NotImplementedError('Abstract method')

    def visit_value_greater_than(self, spec):
        """
        Visit a value greater than specification

        :param spec: a specification instance
        :type spec: :class:`everest.specifications.ValueGreaterThanSpecification`
        """
        raise NotImplementedError('Abstract method')

    def visit_value_less_than_or_equal_to(self, spec):
        """
        Visit a value less than or equal to specification

        :param spec: a specification instance
        :type spec: :class:`everest.specifications.ValueLessThanOrEqualToSpecification`
        """
        raise NotImplementedError('Abstract method')

    def visit_value_greater_than_or_equal_to(self, spec):
        """
        Visit a value greater than or equal to specification

        :param spec: a specification instance
        :type spec: :class:`everest.specifications.ValueGreaterThanOrEqualToSpecification`
        """
        raise NotImplementedError('Abstract method')

    def visit_value_in_range(self, spec):
        """
        Visit a value in range specification

        :param spec: a specification instance
        :type spec: :class:`everest.specifications.ValueInRangeSpecification`
        """
        raise NotImplementedError('Abstract method')


class FilterCqlGenerationVisitor(SpecificationVisitor):
    # FIXME: pylint: disable=W0511
    #        Write more tests and improve implementation

    STARTS_WITH = 'starts-with'
    ENDS_WITH = 'ends-with'
    CONTAINS = 'contains'
    EQUAL_TO = 'equal-to'
    LESS_THAN = 'less-than'
    LESS_OR_EQUALS = 'less-than-or-equal-to'
    GREATER_THAN = 'greater-than'
    GREATER_OR_EQUALS = 'greater-than-or-equal-to'
    IN_RANGE = 'between'
    NEGATION = 'not-'

    __cql_format = '%(attr)s:%(oper)s:%(vals)s'
    __cql_and = '~'
    __cql_range_format = '%(from_value)s-%(to_value)s'

    __cql = None

    def __init__(self):
        SpecificationVisitor.__init__(self)
        self.__cql = self._create_data_dict()

    def visit_conjuction(self, spec):
        pass

    def visit_disjuction(self, spec):
        pass

    def visit_negation(self, spec):
        if not isinstance(spec.wrapped_spec, ValueBoundSpecification):
            raise ValueError('Only value bound specifications can be negated '
                             'in CQL expressions: %s' % spec)
        self.__negate(spec.wrapped_spec)

    def visit_value_starts_with(self, spec):
        self.__append(self.STARTS_WITH, spec.attr_name,
                      self.__value_to_string(spec.attr_value))

    def visit_value_ends_with(self, spec):
        self.__append(self.ENDS_WITH, spec.attr_name,
                      self.__value_to_string(spec.attr_value))

    def visit_value_contains(self, spec):
        self.__append(self.CONTAINS, spec.attr_name,
                      self.__value_to_string(spec.attr_value))

    def visit_value_contained(self, spec):
        for value in spec.attr_value:
            self.__append(self.EQUAL_TO, spec.attr_name,
                          self.__value_to_string(value))

    def visit_value_equal_to(self, spec):
        self.__append(self.EQUAL_TO, spec.attr_name,
                      self.__value_to_string(spec.attr_value))

    def visit_value_less_than(self, spec):
        self.__append(self.LESS_THAN, spec.attr_name,
                      self.__value_to_string(spec.attr_value))

    def visit_value_greater_than(self, spec):
        self.__append(self.GREATER_THAN, spec.attr_name,
                      self.__value_to_string(spec.attr_value))

    def visit_value_less_than_or_equal_to(self, spec):
        self.__append(self.LESS_OR_EQUALS, spec.attr_name,
                      self.__value_to_string(spec.attr_value))

    def visit_value_greater_than_or_equal_to(self, spec):
        self.__append(self.GREATER_OR_EQUALS, spec.attr_name,
                      self.__value_to_string(spec.attr_value))

    def visit_value_in_range(self, spec):
        self.__append(self.IN_RANGE, spec.attr_name,
                      self.__cql_range_format % dict(
                          from_value=self.__value_to_string(spec.from_value),
                          to_value=self.__value_to_string(spec.to_value)
                          )
                      )

    def get_cql(self):
        """
        :returns: a representation of the specification composite as a string
        :rtype: str
        """
        cql_criteria = []
        for attr_name, ops in self.__cql.iteritems():
            for oper_name, values in ops.iteritems():
                data = dict(attr=attr_name.replace('_', '-'), oper=oper_name,
                            vals=','.join(values))
                ctiterion = self.__cql_format % data
                cql_criteria.append(ctiterion.strip())
        return self.__cql_and.join(cql_criteria)

    def _create_data_dict(self):
        return odict()

    def __append(self, operator, attr_name, attr_value):
        """
        """
        if attr_name not in self.__cql:
            self.__cql[attr_name] = self._create_data_dict()
        if operator not in self.__cql[attr_name]:
            self.__cql[attr_name][operator] = []
        self.__cql[attr_name][operator].append(attr_value)

    def __negate(self, spec):
        """
        """
        name = spec.attr_name
        old_oper = self.__cql[spec.attr_name].lastkey()
        if old_oper == self.LESS_THAN:
            new_oper = self.GREATER_OR_EQUALS
        elif old_oper == self.LESS_OR_EQUALS:
            new_oper = self.GREATER_THAN
        elif old_oper == self.GREATER_THAN:
            new_oper = self.LESS_OR_EQUALS
        elif old_oper == self.GREATER_OR_EQUALS:
            new_oper = self.LESS_THAN
        else:
            new_oper = self.NEGATION + old_oper
        self.__cql[name][new_oper] = self.__cql[name][old_oper]
        del self.__cql[name][old_oper]

    def __value_to_string(self, value):
        if isinstance(value, basestring):
            result = '"%s"' % value
        elif IResource.providedBy(value): # pylint: disable=E1101
            result = resource_to_url(value)
        else:
            result = str(value)
        return result


filter_cql_generation_visitor = FilterCqlGenerationVisitor()


class QueryFilterGenerationVisitor(SpecificationVisitor):
    # FIXME: pylint: disable=W0511
    #        Not visiting conjuction/disjuction smells like a bad implementation
    # FIXME: pylint: disable=W0511
    #        This class is almost duplicate to FilterCqlGenerationVisitor

    """
    Implementation of the visitor pattern should be reviewed for efficiency and
    more tests should be written.
    """

    __klass = None
    __clause_factories = {}
    __expr = None

    def __init__(self, klass, clause_factories=None):
        """
        Constructs a QueryFilterGenerationVisitor

        :param klass: a class that is mapped to a selectable using SQLAlchemy
        """
        SpecificationVisitor.__init__(self)
        self.__klass = klass
        if clause_factories is not None:
            self.__clause_factories = clause_factories # FIXME: explain...
        self.__expr = self._create_data_dict()

    def visit_conjuction(self, spec):
        pass

    def visit_disjuction(self, spec):
        pass

    def visit_negation(self, spec):
        if not isinstance(spec.wrapped_spec, ValueBoundSpecification):
            raise ValueError('Only value bound specifications can be negated '
                             'in CQL expressions: %s' % spec)
        self.__negate(spec.wrapped_spec)

    def visit_value_starts_with(self, spec):
        self.__append('starts_with', spec.attr_name, spec.attr_value)

    def visit_value_ends_with(self, spec):
        self.__append('ends_with', spec.attr_name, spec.attr_value)

    def visit_value_contains(self, spec):
        self.__append('contains', spec.attr_name, spec.attr_value)

    def visit_value_contained(self, spec):
        self.__append('contained', spec.attr_name, spec.attr_value)

    def visit_value_equal_to(self, spec):
        self.__append('equal_to', spec.attr_name, spec.attr_value)

    def visit_value_less_than(self, spec):
        self.__append('less_than', spec.attr_name, spec.attr_value)

    def visit_value_greater_than(self, spec):
        self.__append('greater_than', spec.attr_name, spec.attr_value)

    def visit_value_less_than_or_equal_to(self, spec):
        self.__append('less_than_or_equals', spec.attr_name,
                      spec.attr_value)

    def visit_value_greater_than_or_equal_to(self, spec):
        self.__append('greater_than_or_equals', spec.attr_name,
                      spec.attr_value)

    def visit_value_in_range(self, spec):
        range_tuple = (spec.from_value, spec.to_value)
        self.__append('in_range', spec.attr_name, range_tuple)

    def get_expression(self):
        """
        :returns: a representation of the specification in a SQL Expression
        :rtype: :class:`sqlaclhemy.sql._BinaryExpression`
        """
        full_expr = None
        for attr_name, ops in self.__expr.iteritems():
            for oper_name, values in ops.iteritems():
                if (attr_name, oper_name) in self.__clause_factories:
                    expr = self.__clause_factories[(attr_name, oper_name)](values)
                else:
                    op = getattr(self, '_%s_op' % oper_name)
                    attr = getattr(self.__klass, attr_name)

                    clauses = []
                    for value in values:
                        if IResource.providedBy(value): # pylint: disable=E1101
                            value = value.get_entity()
                        clauses.append(op(attr, value))
                    expr = self._or_op(*clauses) # pylint: disable=W0142

                full_expr = self._and_op(full_expr, expr)
        return full_expr

    def _create_data_dict(self):
        return odict()

    def _starts_with_op(self, attr, value):
        return attr.startswith(value)

    def _not_starts_with_op(self, attr, value):
        return self._not_op(self._starts_with_op(attr, value))

    def _ends_with_op(self, attr, value):
        return attr.endswith(value)

    def _not_ends_with_op(self, attr, value):
        return self._not_op(self._ends_with_op(attr, value))

    def _contains_op(self, attr, value):
        return attr.contains(value)

    def _not_contains_op(self, attr, value):
        return self._not_op(self._contains_op(attr, value))

    def _contained_op(self, attr, value):
        return attr.in_(value)

    def _not_contained_op(self, attr, value):
        return self._not_op(self._contained_op(attr, value))

    def _equal_to_op(self, attr, value):
        return attr == value

    def _not_equal_to_op(self, attr, value):
        return self._not_op(self._equal_to_op(attr, value))

    def _less_than_op(self, attr, value):
        return attr < value

    def _less_than_or_equals_op(self, attr, value):
        return attr <= value

    def _greater_than_op(self, attr, value):
        return attr > value

    def _greater_than_or_equals_op(self, attr, value):
        return attr >= value

    def _in_range_op(self, attr, range_tuple):
        from_value, to_value = range_tuple
        return attr.between(from_value, to_value)

    def _not_in_range_op(self, attr, range_tuple):
        return self._not_op(self._in_range_op(attr, range_tuple))

    def _and_op(self, *clauses):
        if clauses[0] is None:
            return sqlalchemy.and_(*clauses[1:]) # pylint: disable=W0142
        else:
            return sqlalchemy.and_(*clauses) # pylint: disable=W0142

    def _or_op(self, *clauses):
        return sqlalchemy.or_(*clauses)

    def _not_op(self, clause):
        return sqlalchemy.not_(clause)

    def __append(self, operator, attr_name, attr_value):
        """
        """
        if attr_name not in self.__expr:
            self.__expr[attr_name] = self._create_data_dict()
        if operator not in self.__expr[attr_name]:
            self.__expr[attr_name][operator] = []
#        if IResource.providedBy(attr_value):
#            value = resource_to_url(attr_value)
#        else:
#            value = attr_value
        self.__expr[attr_name][operator].append(attr_value)

    def __negate(self, spec):
        """
        """
        name = spec.attr_name
        old_oper = self.__expr[spec.attr_name].lastkey()
        if old_oper == 'less_than':
            new_oper = 'greater_than_or_equals'
        elif old_oper == 'less_than_or_equals':
            new_oper = 'greater_than'
        elif old_oper == 'greater_than':
            new_oper = 'less_than_or_equals'
        elif old_oper == 'greater_than_or_equals':
            new_oper = 'less_than'
        else:
            new_oper = 'not_' + old_oper
        self.__expr[name][new_oper] = self.__expr[name][old_oper]
        del self.__expr[name][old_oper]


class SortOrderVisitor(object):
    """
    Abstract base class for all sort order visitors
    """

    def __init__(self):
        if self.__class__ is SortOrderVisitor:
            raise NotImplementedError('Abstract class')

    def visit_simple(self, order):
        """
        Visit a simple order

        :param order: an order instance
        :type order: :class:`everest.sorting.SimpleOrder`
        """
        raise NotImplementedError('Abstract method')

    def visit_natural(self, order):
        """
        Visit a natural order

        :param spec: an order instance
        :type spec: :class:`everest.sorting.NaturalOrder`
        """
        raise NotImplementedError('Abstract method')


class SortOrderGenerationVisitor(SortOrderVisitor):

    __klass = None
    __order_conditions = {}
    __order = None
    __joins = None

    def __init__(self, klass, order_conditions=None):
        """
        Constructs a QueryFilterGenerationVisitor

        :param klass: a class that is mapped to a selectable using SQLAlchemy
        """
        SortOrderVisitor.__init__(self)
        self.__klass = klass
        if order_conditions is not None:
            self.__order_conditions = order_conditions
        self.__order = []
        self.__joins = []

    def visit_simple(self, order):
        attr = self.__get_attr(order.attr_name)
        self.__order.append(attr.asc())

    def visit_natural(self, order):
        # When the visitor visits this order strategy maybe it should try to
        # sort by a special sort key column
        raise NotImplementedError('...to be done...')

    def visit_reverse(self, order):
        if self.__order[-1].modifier is operators.asc_op:
            self.__order[-1] = self.__get_attr(order.wrapped.attr_name).desc()
        else:
            self.__order[-1] = self.__get_attr(order.wrapped.attr_name).asc()

    def visit_conjuction(self, order):
        pass

    def get_order(self):
        return self.__order[:]

    def get_joins(self):
        return self.__joins[:]

    def __get_attr(self, attr_name):
        if attr_name in self.__order_conditions:
            conditions = self.__order_conditions[attr_name]
            if conditions['join'] not in self.__joins:
                self.__joins.append(conditions['join'])
            return conditions['attr']
        else:
            return getattr(self.__klass, attr_name)


class SortOrderKeyFunctionGenerationVisitor(SortOrderVisitor):
    def __init__(self):
        SortOrderVisitor.__init__(self)
        self.__order = []

    def visit_simple(self, order):
        key_func = lambda ent:getattr(ent, order.attr_name)
        self.__order.append(lambda entities: sorted(entities,
                                                    key=key_func))

    def visit_natural(self, order):
        raise NotImplementedError('Not implemented.')

    def visit_reverse(self, order):
        key_func = lambda ent:getattr(ent, order.attr_name)
        self.__order.append(lambda entities: sorted(entities,
                                                    key=key_func,
                                                    reverse=True))

    def get_key_function(self):
        return lambda entities: zip([order_func(entities)
                                     for order_func in self.__order])


class SortOrderCqlGenerationVisitor(SortOrderVisitor):

    __order = None
    __cql_and = '~'
    __cql_asc_op = 'asc'
    __cql_desc_op = 'desc'
    __cql_sep = ':'

    def __init__(self):
        SortOrderVisitor.__init__(self)
        self.__order = []

    def visit_simple(self, order):
        self.__order.append('%s:asc' % self.__to_cql_name(order.attr_name))

    def visit_natural(self, order):
        # When the visitor visits this order strategy maybe it should try to
        # sort by a special sort key column
        raise NotImplementedError('...to be done...')

    def visit_reverse(self, order): # order unused pylint: disable=W0613
        if self.__order[-1].endswith(self.__cql_asc_op):
            self.__order[-1] = self.__switch_op(self.__order[-1],
                                                self.__cql_desc_op)
        else:
            self.__order[-1] = self.__switch_op(self.__order[-1],
                                                self.__cql_asc_op)

    def visit_conjuction(self, order):
        pass

    def get_cql(self):
        return self.__cql_and.join(self.__order)

    def __switch_op(self, val, new_op):
        return self.__cql_sep.join([val.split(self.__cql_sep)[0], new_op])

    def __to_cql_name(self, attr_name):
        return attr_name.replace('_', '-')


sort_order_cql_generation_visitor = SortOrderCqlGenerationVisitor()
