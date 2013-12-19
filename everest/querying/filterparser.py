"""
Filter CQL criteria expression parser.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 5, 2011.
"""
from iso8601.iso8601 import ParseError
from iso8601.iso8601 import parse_date
from pyparsing import CaselessKeyword
from pyparsing import Combine
from pyparsing import Empty
from pyparsing import Forward
from pyparsing import Group
from pyparsing import Literal
from pyparsing import OneOrMore
from pyparsing import Optional
from pyparsing import Regex
from pyparsing import Word
from pyparsing import ZeroOrMore
from pyparsing import alphanums
from pyparsing import alphas
from pyparsing import dblQuotedString
from pyparsing import delimitedList
from pyparsing import nums
from pyparsing import opAssoc
from pyparsing import operatorPrecedence
from pyparsing import replaceWith
from pyparsing import sglQuotedString
from pyparsing import srange
from pyramid.compat import string_types

from everest.entities.utils import identifier_from_slug
from everest.querying.operators import CONTAINED
from everest.querying.operators import CONTAINS
from everest.querying.operators import ENDS_WITH
from everest.querying.operators import EQUAL_TO
from everest.querying.operators import GREATER_OR_EQUALS
from everest.querying.operators import GREATER_THAN
from everest.querying.operators import IN_RANGE
from everest.querying.operators import LESS_OR_EQUALS
from everest.querying.operators import LESS_THAN
from everest.querying.operators import STARTS_WITH
from everest.querying.specifications import cntd
from everest.querying.specifications import cnts
from everest.querying.specifications import ends
from everest.querying.specifications import eq
from everest.querying.specifications import ge
from everest.querying.specifications import gt
from everest.querying.specifications import le
from everest.querying.specifications import lt
from everest.querying.specifications import rng
from everest.querying.specifications import starts
from everest.resources.interfaces import ICollectionResource
from everest.resources.utils import url_to_resource


__docformat__ = 'reStructuredText en'
__all__ = ['parse_filter',
           ]

# Adapted from the iso8601 package to *require* a full yyyy-mm-ddThh:mm:ssZ
# string at the minimum.
ISO8601_REGEX = r'(?P<year>[0-9]{4})' \
                r'-(?P<month>[0-9]{1,2})' \
                r'-(?P<day>[0-9]{1,2})' \
                r'(?P<separator>.)' \
                r'(?P<hour>[0-9]{2})' \
                r':(?P<minute>[0-9]{2})' \
                r':(?P<second>[0-9]{2})' \
                r'(\\.(?P<fraction>[0-9]+))?' \
                r'(?P<timezone>Z|(([-+])([0-9]{2}):([0-9]{2})))?'


AND_PAT = 'and'
OR_PAT = 'or'

BINARY = 2

colon = Literal(':')
comma = Literal(',')
dot = Literal('.')
tilde = Literal('~')
slash = Literal('/')
open_paren = Literal('(')
close_paren = Literal(')')
dbl_quote = Literal('"')
nonzero_nums = srange('[1-9]')
empty = Empty()
true = CaselessKeyword("true").setParseAction(replaceWith(True))
false = CaselessKeyword("false").setParseAction(replaceWith(False))
attribute = Word(alphas, alphanums + '-')
identifier = \
    Combine(attribute + ZeroOrMore('.' + attribute)).setName('identifier')
and_op = CaselessKeyword(AND_PAT).setParseAction(replaceWith(AND_PAT))
or_op = CaselessKeyword(OR_PAT).setParseAction(replaceWith(OR_PAT))


def convert_number(toks):
    str_val = toks[0]
    if '.' in str_val or 'e' in str_val:
        val = float(str_val)
    else:
        val = int(str_val)
    return val


def convert_date(toks):
    date_val = toks[0][0]
    try:
        res = parse_date(date_val)
    except ParseError:
        res = date_val
    return res


def convert_range(toks):
    return (toks.range[0], toks.range[-1])


class CriterionConverter(object):
    spec_map = {STARTS_WITH.name : starts,
                ENDS_WITH.name : ends,
                CONTAINS.name : cnts,
                CONTAINED.name : cntd,
                EQUAL_TO.name : eq,
                GREATER_THAN.name : gt,
                LESS_THAN.name : lt,
                GREATER_OR_EQUALS.name : ge,
                LESS_OR_EQUALS.name : le,
                IN_RANGE.name : rng,
                }

    @classmethod
    def convert(cls, toks):
        crit = toks[0]
        # Extract attribute name.
        attr_name = cls.__prepare_identifier(crit.name)
        # Extract operator name.
        op_name = cls.__prepare_identifier(crit.operator)
        if op_name.startswith("not_"):
            op_name = op_name[4:]
            negate = True
        else:
            negate = False
        # Extract attribute value.
        if len(crit.value) == 0:
            raise ValueError('Criterion does not define a value.')
#        elif len(crit.value) == 1 and isinstance(crit.value, ParseResults):
#            # URLs - convert to resource.
#            url_val = crit.value
#            try:
#                rc = url_to_resource(url_val.resource)
#            except:
#                raise ValueError('Could not convert "%s" to a resource.'
#                                 % url_val.resource)
#            if not url_val.query == '':
#                if not ICollectionResource.providedBy(rc): # pylint: disable=E1101
#                    raise ValueError('Member resources can not have a '
#                                     'query string.')
#                rc.filter = url_val.query
#            attr_value = rc
#            value_is_resource = True
        elif len(crit.value) == 1 \
             and ICollectionResource.providedBy(crit.value[0]): # pylint: disable=E1101
            attr_value = crit.value[0]
            value_is_resource = True
        else:
            attr_value = cls.__prepare_values(crit.value)
            value_is_resource = False
        spec_gen = cls.spec_map[op_name]
        if op_name == CONTAINED.name or value_is_resource:
            spec = spec_gen(**{attr_name:attr_value})
            if negate:
                spec = ~spec
        else:
            # Create a spec for each value and concatenate with OR.
            spec = cls.__make_spec(spec_gen, attr_name, attr_value, negate)
        return spec

    @classmethod
    def __make_spec(cls, spec_gen, attr_name, attr_values, negate):
        spec = None
        for attr_value in attr_values:
            cur_spec = spec_gen(**{attr_name:attr_value})
            if negate:
                cur_spec = ~cur_spec
            if spec is None:
                spec = cur_spec
            else:
                spec = spec | cur_spec
        return spec

    @classmethod
    def __prepare_identifier(cls, name):
        return identifier_from_slug(name)

    @classmethod
    def __prepare_values(cls, values):
        prepared = []
        for val in values:
            if not cls.__is_empty_string(val) and not val in prepared:
                prepared.append(val)
        return prepared

    @classmethod
    def __is_empty_string(cls, v):
        return isinstance(v, string_types) and len(v) == 0


def convert_conjunction(toks):
    left_spec = toks[0][0]
    right_spec = toks[0][-1]
    return left_spec & right_spec


def convert_disjunction(toks):
    left_spec = toks[0][0]
    right_spec = toks[0][-1]
    return left_spec | right_spec


def convert_simple_criteria(toks):
    spec = None
    for crit_spec in toks[0]:
        if spec is None:
            spec = crit_spec
        else:
            spec = spec & crit_spec
    return spec



def convert_string(toks):
    unquoted = toks[0][1:-1]
    if len(url_protocol.searchString(unquoted)) > 0:
        result = [url_to_resource(unquoted)]
    else:
        result = [unquoted]
    return result


# Numbers are converted to ints if possible.
cql_number = Combine(Optional('-') + ('0' | Word(nonzero_nums, nums)) +
                     Optional('.' + Word(nums)) +
                     Optional(Word('eE', exact=1) + Word(nums + '+-', nums))
                     ).setParseAction(convert_number)
# Dates are parsed as double-quoted ISO8601 strings and converted to datetime
# objects.
cql_date = Combine(dbl_quote.suppress() + Regex(ISO8601_REGEX) +
                   dbl_quote.suppress()
                   ).setParseAction(convert_date)
# All double-quoted strings that are not dates are returned with their quotes
# removed.
cql_string = (dblQuotedString | sglQuotedString).setParseAction(convert_string)

# URLs are detected as strings starting with the http(s) protocol.
url_protocol = Combine(Literal('http') + Optional('s'))

# Number range.
# FIXME: char ranges are not supported yet
cql_number_range = Group(cql_number + '-' + cql_number
                           ).setParseAction(convert_range)

cql_values = Group(delimitedList(
                        cql_number_range('range') |
                        cql_number('number') |
                        cql_date('date') |
                        cql_string('string') |
                        true |
                        false |
                        empty
                        )
                   )

logical_op = and_op('operator') | or_op('operator')

criterion = Group(identifier('name') + colon.suppress() +
                  identifier('operator') + colon.suppress() +
                  cql_values('value')
                  )
criterion.setParseAction(CriterionConverter.convert)

# Recursive definition of "junction" (AND or OR) clauses.
junctions = Forward()
junction_element = (criterion |
                    open_paren.suppress() + junctions +
                    close_paren.suppress())
junctions << operatorPrecedence(# pylint: disable=W0106
                    junction_element,
                    [(and_op, BINARY, opAssoc.LEFT, convert_conjunction),
                     (or_op, BINARY, opAssoc.LEFT, convert_disjunction),
                     ])

# Old-style criteria separated by "~".
simple_criteria = Group(criterion +
                        OneOrMore(tilde.suppress() + criterion))
simple_criteria.setParseAction(convert_simple_criteria)

query = (simple_criteria | junctions) # pylint: disable=W0104


def parse_filter(query_string):
    """
    Parses the given filter criteria string.
    """
    return query.parseString(query_string)[0]
