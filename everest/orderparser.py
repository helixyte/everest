"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 5, 2011.
"""

from pyparsing import Group
from pyparsing import Literal
from pyparsing import Word
from pyparsing import alphas
from pyparsing import delimitedList
from pyparsing import oneOf

__docformat__ = 'reStructuredText en'
__all__ = ['order_parser',
           ]


colon = Literal(':')
tilde = Literal('~')
identifier = Word(alphas, alphas + '-').setName('identifier')
direction = oneOf("asc desc").setName('direction')
sort_order = Group(identifier('name') + colon.suppress() + \
                   direction('operator')).setResultsName('order')
order_parser = Group(delimitedList(sort_order, tilde)).setResultsName('order')
