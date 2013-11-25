"""
Order CQL expression parser.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 5, 2011.
"""
from everest.entities.utils import identifier_from_slug
from everest.querying.operators import ASCENDING
from everest.querying.operators import DESCENDING
from everest.querying.specifications import asc
from everest.querying.specifications import desc
from pyparsing import Combine
from pyparsing import Group
from pyparsing import Literal
from pyparsing import Word
from pyparsing import ZeroOrMore
from pyparsing import alphas
from pyparsing import oneOf
from pyparsing import opAssoc
from pyparsing import operatorPrecedence

__docformat__ = 'reStructuredText en'
__all__ = ['parse_order',
           ]


colon = Literal(':')
tilde = Literal('~')
attribute = Word(alphas, alphas + '-')
identifier = Combine(attribute + ZeroOrMore('.' + attribute)
                     ).setName('identifier')
direction = oneOf("asc desc").setName('direction')

BINARY = 2

class CriterionConverter(object):
    spec_map = {ASCENDING.name:asc,
                DESCENDING.name:desc}

    @classmethod
    def convert(cls, seq):
        crit = seq[0]
        name = cls.__prepare_identifier(crit.name)
        op_name = cls.__prepare_identifier(crit.operator)
        return cls.__make_spec(name, op_name)

    @classmethod
    def __prepare_identifier(cls, name):
        return identifier_from_slug(name)

    @classmethod
    def __make_spec(cls, name, op_name):
        spec_gen = cls.spec_map[op_name]
        return spec_gen(name)


def convert_junction(seq):
    left_spec = seq[0][0]
    right_spec = seq[0][-1]
    return left_spec & right_spec


criterion = Group(identifier('name') + colon.suppress() + \
                  direction('operator')).setResultsName('order')
criterion.setParseAction(CriterionConverter.convert)
criteria = \
    operatorPrecedence(criterion,
                       [
                        (tilde, BINARY, opAssoc.LEFT, convert_junction)
                        ])

order = criteria | criterion


def parse_order(criteria_string):
    """
    Parses the given order criteria string.
    """
    return order.parseString(criteria_string)[0]
