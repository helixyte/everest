"""
Filter CQL criteria expression parser.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 5, 2011.
"""
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
from pyparsing import alphas
from pyparsing import dblQuotedString
from pyparsing import delimitedList
from pyparsing import nums
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

colon = Literal(':')
comma = Literal(',')
dot = Literal('.')
tilde = Literal('~')
slash = Literal('/')
open_paren = Literal(OPEN_PAREN_PAT).setParseAction(replaceWith('open-group'))
close_paren = Literal(CLOSE_PAREN_PAT).setParseAction(replaceWith('close-group'))
dbl_quote = Literal('"')
nonzero_nums = srange('[1-9]')
empty = Empty()
true = CaselessKeyword("true").setParseAction(replaceWith(True))
false = CaselessKeyword("false").setParseAction(replaceWith(False))
attribute = Word(alphas, alphas + '-')
identifier = \
    Combine(attribute + ZeroOrMore('.' + attribute)).setName('identifier')
and_ = CaselessKeyword(AND_PAT).setParseAction(replaceWith(AND_PAT))
or_ = CaselessKeyword(OR_PAT).setParseAction(replaceWith(OR_PAT))

#
open_paren_parsed = open_paren('operator') \
                        .setParseAction(replaceWith('open-group')) \
                        .searchString(OPEN_PAREN_PAT)
close_paren_parsed = close_paren('operator') \
                        .setParseAction(replaceWith('close-group')) \
                        .searchString(CLOSE_PAREN_PAT)



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


def convert_simple_criteria(seq):
    toks = seq[0]
    res = open_paren_parsed + toks + close_paren_parsed
    return res


def convert_op_criteria(seq):
    res = seq[0]
    return res


def convert_query(seq):
    return seq[0]


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

logical_op = Group(and_('operator') | or_('operator'))

criterion = Group(identifier('name') + colon.suppress() +
                  identifier('operator') + colon.suppress() +
                  cql_values('value')
                  )

tilde_op = Group(tilde('operator').setParseAction(replaceWith(AND_PAT)))


# Criteria group with arbitrary logical operator as separator.
op_criteria = Group(criterion +
                    ZeroOrMore(logical_op + criterion))

# A simple criteria group not using parentheses.
simple_op_criteria = op_criteria.copy()
simple_op_criteria.setParseAction(convert_simple_criteria)

# Simple criteria group using tilde character as separator (signifies AND).
simple_tilde_criteria = Group(criterion +
                            OneOrMore(tilde_op + criterion))
simple_tilde_criteria.setParseAction(convert_simple_criteria)

# Explicitly grouped criteria.
grouped_criteria = Forward()
grouped_op_criteria = op_criteria.copy()
grouped_op_criteria.setParseAction(convert_op_criteria)
grouped_criteria_item = grouped_op_criteria | grouped_criteria
grouped_criteria << (Group(open_paren('operator')) + # pylint: disable=W0106
                     grouped_criteria_item +
                     ZeroOrMore(logical_op + grouped_criteria_item) +
                     Group(close_paren('operator')))

query_criteria = grouped_criteria | simple_op_criteria

query = Group(simple_tilde_criteria |
              (query_criteria + ZeroOrMore(logical_op + query_criteria)))
query.setParseAction(convert_query)

#criteria = \
#    (Group(delimitedList(criterion, tilde)) |
#     Group(delimitedList(criterion, logical_op))).setResultsName('criteria')



def parse_filter(query_string):
    """
    Parses the given filter criteria string.
    """
    return query.parseString(query_string)
