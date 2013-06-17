"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 11, 2013.
"""
from everest.constants import CARDINALITIES
from everest.constants import Cardinality
from everest.testing import Pep8CompliantTestCase

__docformat__ = 'reStructuredText en'
__all__ = ['CardinalityConstantsTestCase',
           ]


class CardinalityConstantsTestCase(Pep8CompliantTestCase):
    def test_new(self):
        with self.assert_raises(ValueError) as cm:
            dummy = Cardinality('foo', 'bar')
        self.assert_true(cm.exception.message.startswith('"relator" and'))

    def test_str(self):
        self.assert_true(str(CARDINALITIES.MANYTOONE).startswith('*->'))
