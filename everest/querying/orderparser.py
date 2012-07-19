"""
Order CQL expression parser.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 5, 2011.
"""
from pyparsing import Combine
from pyparsing import Group
from pyparsing import Literal
from pyparsing import Word
from pyparsing import ZeroOrMore
from pyparsing import alphas
from pyparsing import delimitedList
from pyparsing import oneOf

__docformat__ = 'reStructuredText en'
__all__ = ['parse_order',
           ]


colon = Literal(':')
tilde = Literal('~')
attribute = Word(alphas, alphas + '-')
identifier = Combine(attribute + ZeroOrMore('.' + attribute)
                     ).setName('identifier')
direction = oneOf("asc desc").setName('direction')
order_criterion = Group(identifier('name') + colon.suppress() + \
                   direction('operator')).setResultsName('order')
order_criteria = \
    Group(delimitedList(order_criterion, tilde)).setResultsName('criteria')


def parse_order(criteria_string):
    """
    Parses the given order criteria string.
    """
    return order_criteria.parseString(criteria_string)
