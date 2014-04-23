"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 11, 2013.
"""
import pytest

from everest.constants import CARDINALITIES
from everest.constants import CARDINALITY_CONSTANTS
from everest.constants import Cardinality


__docformat__ = 'reStructuredText en'
__all__ = ['TestConstants',
           ]


class TestConstants(object):
    def test_iterable(self):
        assert set(CARDINALITY_CONSTANTS) == \
                          set((CARDINALITY_CONSTANTS.ONE,
                               CARDINALITY_CONSTANTS.MANY))

    def test_new_cardinality(self):
        with pytest.raises(ValueError) as cm:
            dummy = Cardinality('foo', 'bar')
        assert str(cm.value).startswith('"relator" and')

    def test_str_cardinality(self):
        assert str(CARDINALITIES.MANYTOONE).startswith('*->')
