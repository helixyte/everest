"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 16, 2013.
"""
from everest.attributes import get_attribute_cardinality
from everest.constants import CARDINALITY_CONSTANTS
from everest.resources.base import Member
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from everest.testing import Pep8CompliantTestCase
from everest.attributes import is_terminal_attribute

__docformat__ = 'reStructuredText en'
__all__ = ['AttributesTestCase',
           ]


class AttributesTestCase(Pep8CompliantTestCase):
    def set_up(self):
        self.member_attr = member_attribute(Member, 'attr')
        self.terminal_attr = terminal_attribute(int, 'attr')

    def test_get_attribute_cardinality(self):
        self.assert_equal(get_attribute_cardinality(self.member_attr),
                          CARDINALITY_CONSTANTS.ONE)
        self.assert_raises(ValueError, get_attribute_cardinality,
                           self.terminal_attr)

    def test_is_terminal_attribute(self):
        self.assert_true(is_terminal_attribute(self.terminal_attr))
        self.assert_false(is_terminal_attribute(self.member_attr))

