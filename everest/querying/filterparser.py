"""
Filter CQL criteria expression parser.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 5, 2011.
"""
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
from everest.resources.utils import url_to_resource
from iso8601.iso8601 import parse_date
from pyparsing import CaselessKeyword
from pyparsing import CharsNotIn
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
from pyparsing import removeQuotes
from pyparsing import replaceWith
from pyparsing import srange

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
OPEN_PAREN_PAT = '('
CLOSE_PAREN_PAT = ')'

BINARY = 2

colon = Literal(':')
comma = Literal(',')
dot = Literal('.')
tilde = Literal('~')
slash = Literal('/')
open_paren = Literal(OPEN_PAREN_PAT)
close_paren = Literal(CLOSE_PAREN_PAT)
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


def convert_number(seq):
    """
    pyparsing action that converts the given 1-element number string 
    sequence into a float or an integer.
    """
    str_val = seq[0]
    if '.' in str_val or 'e' in str_val:
        val = float(str_val)
    else:
        val = int(str_val)
    return val


def convert_date(seq):
    date_val = seq[0][0]
    try:
        res = parse_date(date_val)
    except ValueError:
        res = date_val
    return res


def convert_range(seq):
    return (seq.range[0], seq.range[-1])


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
    def convert(cls, seq):
        crit = seq[0]
        op_name = cls.__prepare_identifier(crit.operator)
        if op_name.startswith("not_"):
            op_name = op_name[4:]
            negate = True
        else:
            negate = False
        attr_name = cls.__prepare_identifier(crit.name)
        attr_values = cls.__prepare_values(crit.value)
        if attr_values == []:
            raise ValueError('Criterion does not define a value.')
        # For the CONTAINED spec, we treat all parsed values as one value.
        if op_name == CONTAINED.name:
            attr_values = [attr_values]
        spec_gen = cls.spec_map[op_name]
        return cls.__make_spec(spec_gen, attr_name, attr_values, negate)

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
            if cls.__is_empty_string(val):
                continue
            elif cls.__is_url(val):
                # URLs - convert to resource.
                val = url_to_resource(''.join(val))
            if not val in prepared:
                prepared.append(val)
        return prepared

    @classmethod
    def __is_empty_string(cls, v):
        return isinstance(v, basestring) and len(v) == 0

    @classmethod
    def __is_url(cls, v):
        return isinstance(v, basestring) and v.startswith('http://')


def convert_conjunction(seq):
    left_spec = seq[0][0]
    right_spec = seq[0][-1]
    return left_spec & right_spec


def convert_disjunction(seq):
    left_spec = seq[0][0]
    right_spec = seq[0][-1]
    return left_spec | right_spec


def convert_simple_criteria(seq):
    spec = None
    for crit_spec in seq[0]:
        if spec is None:
            spec = crit_spec
        else:
            spec = spec & crit_spec
    return spec


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
cql_string = dblQuotedString.setParseAction(removeQuotes)

# URLs
protocol = Literal('http')
domain = Combine(OneOrMore(CharsNotIn('/')))
path = Combine(slash + OneOrMore(CharsNotIn(',~?&')))
cql_url = Combine(protocol + '://' + domain + path)

# Number range.
# FIXME: char ranges are not supported yet
cql_number_range = Group(cql_number + '-' + cql_number
                           ).setParseAction(convert_range)

cql_values = Group(
    delimitedList(
        cql_number_range('range') |
        cql_number('number') |
        cql_date('date') |
        cql_string('string') |
        cql_url('url') |
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

junction_element = Forward()
junction = operatorPrecedence(
                    junction_element,
                    [
                     (and_op, BINARY, opAssoc.LEFT, convert_conjunction),
                     (or_op, BINARY, opAssoc.LEFT, convert_disjunction),
                     ])
junction_element << (criterion | # pylint: disable=W0106
                     open_paren.suppress() + junction + close_paren.suppress())
# Safeguard against left-recursive grammars.
junction.validate()

simple_criteria = Group(criterion +
                        OneOrMore(tilde.suppress() + criterion))
simple_criteria.setParseAction(convert_simple_criteria)

query = simple_criteria | junction


def parse_filter(query_string):
    """
    Parses the given filter criteria string.
    """
    return query.parseString(query_string)[0]
