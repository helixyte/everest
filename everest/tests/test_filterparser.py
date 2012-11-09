"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 4, 2011.
"""
from datetime import datetime
from everest.querying.filterparser import parse_filter
from everest.querying.operators import ENDS_WITH
from everest.querying.operators import EQUAL_TO
from everest.querying.operators import GREATER_THAN
from everest.querying.operators import STARTS_WITH
from everest.querying.specifications import ConjunctionFilterSpecification
from everest.querying.specifications import DisjunctionFilterSpecification
from everest.querying.specifications import ValueEqualToFilterSpecification
from everest.querying.specifications import ValueGreaterThanFilterSpecification
from everest.querying.specifications import ValueLessThanFilterSpecification
from everest.querying.specifications import ValueStartsWithFilterSpecification
from everest.testing import TestCaseWithConfiguration
from pyparsing import ParseException

__docformat__ = 'reStructuredText en'
__all__ = ['QueryParserTestCase',
           ]


class QueryParserTestCase(TestCaseWithConfiguration):
    parser = None

    def set_up(self):
        TestCaseWithConfiguration.set_up(self)
        self.parser = parse_filter

    def test_no_criterion_query(self):
        expr = ''
        self.assert_raises(ParseException, self.parser, expr)

    def test_one_criterion_query(self):
        expr = 'name:equal-to:"Nikos"'
        result = self.parser(expr)
        self.assert_true(isinstance(result, ValueEqualToFilterSpecification))
        self.assert_equal(result.attr_name, 'name')
        self.assert_equal(result.operator, EQUAL_TO)
        self.assert_equal(result.attr_value, 'Nikos')

    def test_one_criterion_query_with_many_values(self):
        expr = 'name:equal-to:"Nikos","Oliver","Andrew"'
        result = self.parser(expr)
        self.assert_true(isinstance(result,
                                    DisjunctionFilterSpecification))
        self.assert_true(isinstance(result.left_spec,
                                    DisjunctionFilterSpecification))
        self.assert_true(isinstance(result.right_spec,
                                    ValueEqualToFilterSpecification))
        self.assert_equal(result.left_spec.left_spec.attr_name, 'name')
        self.assert_equal(result.left_spec.left_spec.operator, EQUAL_TO)
        self.assert_equal(result.left_spec.left_spec.attr_value, 'Nikos')
        self.assert_equal(result.left_spec.right_spec.attr_name, 'name')
        self.assert_equal(result.left_spec.right_spec.operator, EQUAL_TO)
        self.assert_equal(result.left_spec.right_spec.attr_value, 'Oliver')
        self.assert_equal(result.right_spec.attr_name, 'name')
        self.assert_equal(result.right_spec.operator, EQUAL_TO)
        self.assert_equal(result.right_spec.attr_value, 'Andrew')

    def test_mixed_criteria_query(self):
        expr = 'name:starts-with:"Ni" OR name:ends-with:"kos" ' \
               'AND age:equal-to:34'
        result = self.parser(expr)
        self.assert_true(isinstance(result,
                                    DisjunctionFilterSpecification))
        self.assert_true(isinstance(result.left_spec,
                                    ValueStartsWithFilterSpecification))
        self.assert_true(isinstance(result.right_spec,
                                    ConjunctionFilterSpecification))
        self.assert_equal(result.left_spec.attr_name, 'name')
        self.assert_equal(result.right_spec.left_spec.attr_name, 'name')
        self.assert_equal(result.right_spec.right_spec.attr_name, 'age')

    def test_mixed_criteria_query_with_parens(self):
        expr = '(name:starts-with:"Ni" AND name:ends-with:"kos") ' \
               'OR age:equal-to:34'
        result = self.parser(expr)
        self.assert_true(isinstance(result,
                                    DisjunctionFilterSpecification))
        self.assert_true(isinstance(result.left_spec,
                                    ConjunctionFilterSpecification))
        self.assert_true(isinstance(result.right_spec,
                                    ValueEqualToFilterSpecification))
        self.assert_equal(result.left_spec.left_spec.attr_name, 'name')
        self.assert_equal(result.left_spec.right_spec.attr_name, 'name')
        self.assert_equal(result.right_spec.attr_name, 'age')

    def test_nested_criteria_query(self):
        expr0 = '(name:starts-with:"Ni" AND ' \
               ' (name:ends-with:"kos" OR age:equal-to:34))'
        result0 = self.parser(expr0)
        self.assert_true(isinstance(result0, ConjunctionFilterSpecification))
        expr1 = '((name:starts-with:"Ni" AND name:ends-with:"kos") ' \
               'OR age:equal-to:34))'
        result1 = self.parser(expr1)
        self.assert_true(isinstance(result1, DisjunctionFilterSpecification))

    def test_multiple_criterion_query(self):
        def _test(expr):
            result = self.parser(expr)
            self.assert_true(isinstance(result,
                                        ConjunctionFilterSpecification))
            spec1 = result.left_spec
            spec2 = result.right_spec
            self.assert_equal(spec1.attr_name, 'name')
            self.assert_equal(spec1.operator, STARTS_WITH)
            self.assert_equal(spec1.attr_value, 'Ni')
            self.assert_equal(spec2.attr_name, 'name')
            self.assert_equal(spec2.operator, ENDS_WITH)
            self.assert_equal(spec2.attr_value, 'kos')
        crits = ['name:starts-with:"Ni"', 'name:ends-with:"kos"']
        for expr in ('~'.join(crits),
                     ' AND '.join(crits),
                     '(%s)' % ' AND '.join(crits)
                     ):
            _test(expr)

    def test_one_criterion_query_with_integers(self):
        expr = 'age:equal-to:34,44'
        result = self.parser(expr)
        self.assert_true(isinstance(result,
                                    DisjunctionFilterSpecification))
        self.assert_true(isinstance(result.left_spec,
                                    ValueEqualToFilterSpecification))
        self.assert_true(isinstance(result.right_spec,
                                    ValueEqualToFilterSpecification))
        self.assert_equal(result.left_spec.attr_name, 'age')
        self.assert_equal(result.left_spec.operator, EQUAL_TO)
        self.assert_equal(result.left_spec.attr_value, 34)
        self.assert_equal(result.right_spec.attr_name, 'age')
        self.assert_equal(result.right_spec.operator, EQUAL_TO)
        self.assert_equal(result.right_spec.attr_value, 44)

    def test_one_criterion_query_with_integer_scientific_format(self):
        expr = 'volume:greater-than:5e+05'
        result = self.parser(expr)
        self.assert_true(isinstance(result,
                                    ValueGreaterThanFilterSpecification))
        self.assert_equal(result.attr_name, 'volume')
        self.assert_equal(result.operator, GREATER_THAN)
        self.assert_equal(result.attr_value, 500000)

    def test_one_criterion_query_with_floats(self):
        expr = 'cost:greater-than:3.14'
        result = self.parser(expr)
        self.assert_true(isinstance(result,
                                    ValueGreaterThanFilterSpecification))
        self.assert_equal(result.attr_name, 'cost')
        self.assert_equal(result.operator, GREATER_THAN)
        self.assert_equal(result.attr_value, 3.14)

    def test_one_criterion_query_with_floats_scientific_format(self):
        expr = 'volume:greater-than:5.5e-05'
        result = self.parser(expr)
        self.assert_true(isinstance(result,
                                    ValueGreaterThanFilterSpecification))
        self.assert_equal(result.attr_name, 'volume')
        self.assert_equal(result.operator, GREATER_THAN)
        self.assert_equal(result.attr_value, 5.5e-05)

    def test_one_criterion_query_with_floats_scientific_format_negative(self):
        expr = 'volume:greater-than:5e-05'
        result = self.parser(expr)
        self.assert_true(isinstance(result,
                                    ValueGreaterThanFilterSpecification))
        self.assert_equal(result.attr_name, 'volume')
        self.assert_equal(result.operator, GREATER_THAN)
        self.assert_equal(result.attr_value, 5e-05)

    def _test_multiple_criterion_query_with_different_value_types(self, expr):
        result = self.parser(expr)
        self.assert_true(isinstance(result,
                                    ConjunctionFilterSpecification))
        self.assert_true(isinstance(result.left_spec,
                                    ConjunctionFilterSpecification))
        self.assert_true(isinstance(result.left_spec.left_spec,
                                    ConjunctionFilterSpecification))
        self.assert_true(isinstance(result.left_spec.left_spec.left_spec,
                                    DisjunctionFilterSpecification))
        self.assert_true(
            isinstance(result.left_spec.left_spec.left_spec.left_spec,
                       DisjunctionFilterSpecification))
        self.assert_true(isinstance(result.right_spec,
                                    DisjunctionFilterSpecification))
        spec1 = result.left_spec.left_spec.left_spec.left_spec.left_spec
        spec2 = result.left_spec.left_spec.left_spec.left_spec.right_spec
        spec3 = result.right_spec.left_spec
        spec4 = result.right_spec.right_spec
        self.assert_equal(spec1.attr_name, 'name')
        self.assert_equal(spec1.operator, STARTS_WITH)
        self.assert_equal(spec1.attr_value, 'Ni')
        self.assert_equal(spec2.attr_name, 'name')
        self.assert_equal(spec2.operator, STARTS_WITH)
        self.assert_equal(spec2.attr_value, 'Ol')
        self.assert_equal(spec3.attr_name, 'discount')
        self.assert_equal(spec3.operator, EQUAL_TO)
        self.assert_equal(spec3.attr_value, -20)
        self.assert_equal(spec4.attr_name, 'discount')
        self.assert_equal(spec4.operator, EQUAL_TO)
        self.assert_equal(spec4.attr_value, -30)

    def test_multiple_criterion_query_with_different_value_types(self):
        expr = 'name:starts-with:"Ni","Ol","An"~' \
               'age:equal-to:34,44,54~' \
               'phone-number:starts-with:1,2,3~' \
               'discount:equal-to:-20,-30~'
        self._test_multiple_criterion_query_with_different_value_types(expr)

    def test_multiple_criterion_query_with_misplaced_commas(self):
        expr = 'name:starts-with:"Ni", "Ol", ,"An"~' \
               'age:equal-to:34, 44, 54,~' \
               'phone-number:starts-with:,1,2,3~' \
               'discount:equal-to:,-20,,-30,'
        self._test_multiple_criterion_query_with_different_value_types(expr)

    def test_one_text_criterion_query_with_spaces(self):
        expr = 'name:equal-to:"Nikos Papagrigoriou"'
        result = self.parser(expr)
        self.assert_true(isinstance(result, ValueEqualToFilterSpecification))
        self.assert_equal(result.attr_value, 'Nikos Papagrigoriou')

    def test_invalid_criterion_with_only_comma_as_value(self):
        expr = 'name:equal-to:,'
        self.assert_raises(ValueError, self.parser, expr)

    def test_float_and_int(self):
        expr = 'age:less-than:12~height:less-than:5.2'
        result = self.parser(expr)
        self.assert_true(isinstance(result, ConjunctionFilterSpecification))
        self.assert_equal(result.left_spec.attr_value, 12)
        self.assert_true(result.right_spec.attr_value, 5.2)

    def test_valid_dotted_names(self):
        expr = 'user.age:less-than:12'
        result = self.parser(expr)
        self.assert_true(isinstance(result,
                                    ValueLessThanFilterSpecification))
        self.assert_equal(result.attr_name, 'user.age')
        expr = 'user.address.street:equal-to:"Main"'
        result = self.parser(expr)
        self.assert_true(isinstance(result,
                                    ValueEqualToFilterSpecification))
        self.assert_equal(result.attr_name, 'user.address.street')

    def test_invalid_dotted_names(self):
        expr = 'user.age.:less-than:12'
        self.assert_raises(ParseException, self.parser, expr)
        expr = '.user.age:less-than:12'
        self.assert_raises(ParseException, self.parser, expr)
        expr = 'user..age:less-than:12'
        self.assert_raises(ParseException, self.parser, expr)

    def test_valid_date(self):
        expr = 'birthday:equal-to:"1966-04-21T15:23:01Z"'
        result = self.parser(expr)
        self.assert_true(isinstance(result,
                                    ValueEqualToFilterSpecification))
        dt = result.attr_value
        self.assert_true(isinstance(dt, datetime))
        self.assert_equal(dt.year, 1966)
        self.assert_equal(dt.month, 4)
        self.assert_equal(dt.day, 21)
        self.assert_equal(dt.hour, 15)
        self.assert_equal(dt.minute, 23)
        self.assert_equal(dt.second, 1)

    def test_invalid_dates(self):
        def _check_expr(expr):
            result = self.parser(expr)
            self.assert_true(isinstance(result,
                                        ValueEqualToFilterSpecification))
            self.assert_false(isinstance(result.attr_value, datetime))
        # Violations of the regex.
        expr = 'birthday:equal-to:"19661-04-21T15:23:00Z"'
        _check_expr(expr)
        expr = 'birthday:equal-to:"19661-041-21T15:23:00Z"'
        _check_expr(expr)
        expr = 'birthday:equal-to:"1966-04-211T15:23:00Z"'
        _check_expr(expr)
        expr = 'birthday:equal-to:"1966-04-21T151:23:00Z"'
        _check_expr(expr)
        expr = 'birthday:equal-to:"1966-04-21T15:231:00Z"'
        _check_expr(expr)
        # Violations of the allowed values.
        expr = 'birthday:equal-to:"1966-13-21T15:23:00Z"'
        _check_expr(expr)
        expr = 'birthday:equal-to:"1966-04-32T15:23:00Z"'
        _check_expr(expr)
        expr = 'birthday:equal-to:"1966-04-21T24:23:00Z"'
        _check_expr(expr)
        expr = 'birthday:equal-to:"1966-04-21T15:61:00Z"'
        _check_expr(expr)
