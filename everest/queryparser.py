"""
This file is part of the everest project. 
See LICENSE.txt for licensing, AUTHORS.txt for contributor information.

Created on Jul 5, 2011.
"""

from pyparsing import CaselessKeyword
from pyparsing import CharsNotIn
from pyparsing import Combine
from pyparsing import Empty
from pyparsing import Group
from pyparsing import Literal
from pyparsing import OneOrMore
from pyparsing import Optional
from pyparsing import Word
from pyparsing import alphas
from pyparsing import dblQuotedString
from pyparsing import delimitedList
from pyparsing import nums
from pyparsing import removeQuotes
from pyparsing import replaceWith

__docformat__ = 'reStructuredText en'
__all__ = ['query_parser',
           ]

colon = Literal(':')
comma = Literal(',')
dot = Literal('.')
tilde = Literal('~')
slash = Literal('/')
empty = Empty()
true = CaselessKeyword("true").setParseAction(replaceWith(True))
false = CaselessKeyword("false").setParseAction(replaceWith(False))
identifier = Word(alphas, alphas + '-').setName('identifier')
cql_string = dblQuotedString.setParseAction(removeQuotes)
cql_number = Combine(Optional('-') + ('0' | Word('123456789', nums)) + \
                     Optional('.' + Word(nums)) + \
                     Optional(Word('eE', exact=1) + Word(nums + '+-', nums))
                     ).setParseAction(lambda t: float(t[0]))
protocol = Literal('http')
domain = Combine(OneOrMore(CharsNotIn('/')))
path = Combine(slash + OneOrMore(CharsNotIn(',~?&')))
cql_url = Combine(protocol + '://' + domain + path)

# FIXME: Dates and value ranges are not supported yet # pylint:disable=W0511
cql_elements = Group(
    delimitedList(
        cql_string('string') | \
        cql_number('number') | \
        cql_url('url') | \
        true | \
        false | \
        empty
        )
    )

criterion = Group(identifier('name') + colon.suppress() + \
                  identifier('operator') + colon.suppress() + \
                  cql_elements('value')
                  ).setResultsName('criterion')
query_parser = Group(delimitedList(criterion, tilde)).setResultsName('criteria')
