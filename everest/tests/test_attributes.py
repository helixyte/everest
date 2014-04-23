"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 16, 2013.
"""
import pytest

from everest.attributes import get_attribute_cardinality
from everest.attributes import is_terminal_attribute
from everest.constants import CARDINALITY_CONSTANTS
from everest.resources.base import Member
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute


__docformat__ = 'reStructuredText en'
__all__ = ['TestAttributes',
           ]


class TestAttributes(object):
    @pytest.mark.parametrize('attr_name', ['attr'])
    def test_get_attribute_cardinality(self, attr_name):
        mb_attr = member_attribute(Member, attr_name)
        assert get_attribute_cardinality(mb_attr) == CARDINALITY_CONSTANTS.ONE
        t_attr = terminal_attribute(int, attr_name)
        with pytest.raises(ValueError):
            get_attribute_cardinality(t_attr)

    @pytest.mark.parametrize('attr_name', ['attr'])
    def test_is_terminal_attribute(self, attr_name):
        mb_attr = member_attribute(Member, attr_name)
        assert is_terminal_attribute(mb_attr) is False
        t_attr = terminal_attribute(int, attr_name)
        assert is_terminal_attribute(t_attr) is True
