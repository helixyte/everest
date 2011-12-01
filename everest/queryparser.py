"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 5, 2011.
"""

#from iso8601.iso8601 import ISO8601_REGEX
from iso8601.iso8601 import parse_date
from pyparsing import CaselessKeyword
from pyparsing import CharsNotIn
from pyparsing import Combine
from pyparsing import Empty
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
__all__ = ['parse_query',
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


colon = Literal(':')
comma = Literal(',')
dot = Literal('.')
tilde = Literal('~')
slash = Literal('/')
dbl_quote = Literal('"')
nonzero_nums = srange('[1-9]')
empty = Empty()
true = CaselessKeyword("true").setParseAction(replaceWith(True))
false = CaselessKeyword("false").setParseAction(replaceWith(False))
attribute = Word(alphas, alphas + '-')
identifier = Combine(attribute + ZeroOrMore('.' + attribute)
                     ).setName('identifier')

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

# FIXME: Value ranges are not supported yet # pylint:disable=W0511
cql_values = Group(
    delimitedList(
        cql_number('number') |
        cql_date('date') |
        cql_string('string') |
        cql_url('url') |
        true |
        false |
        empty
        )
    )

criterion = Group(identifier('name') + colon.suppress() +
                  identifier('operator') + colon.suppress() +
                  cql_values('value')
                  )
criteria = Group(delimitedList(criterion, tilde)).setResultsName('criteria')

parse_query = criteria.parseString
