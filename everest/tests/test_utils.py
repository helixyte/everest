"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 18, 2011.
"""

from everest.testing import Pep8CompliantTestCase
from everest.utils import classproperty
from everest.utils import get_traceback
from everest.utils import BidirectionalLookup

__docformat__ = 'reStructuredText en'
__all__ = ['UtilsTestCase',
           ]


class UtilsTestCase(Pep8CompliantTestCase):

    def test_classproperty(self):
        class X(object):
            attr = 'myattr'
            @classproperty
            def clsprop(cls): # no self as first arg pylint: disable=E0213
                return cls.attr
        self.assert_equal(X.clsprop, X.attr)

    def test_get_traceback(self):
        try:
            raise RuntimeError('Something went wrong.')
        except RuntimeError:
            tb = get_traceback()
        self.assert_true(tb.startswith('Traceback (most recent call last)'))
        self.assert_true(tb.rstrip().endswith(
                                    'RuntimeError: Something went wrong.'))

    def test_bidirectional_lookup(self):
        bl = BidirectionalLookup(dict(a=1, b=2))
        self.assert_true(bl.has_left('a'))
        self.assert_true(bl.has_right(1))
        self.assert_false(bl.has_right('a'))
        self.assert_false(bl.has_left(1))
        self.assert_equal(bl.get_left('a'), 1)
        self.assert_equal(bl.get_right(1), 'a')
        self.assert_equal(bl.pop_left('a'), 1)
        self.assert_false(bl.has_left('a'))
        self.assert_false(bl.has_right(1))
        self.assert_equal(bl.left_keys(), ['b'])
        self.assert_equal(bl.right_keys(), [2])
        self.assert_equal(bl.left_values(), [2])
        self.assert_equal(bl.right_values(), ['b'])
        self.assert_equal(bl.left_items(), [('b', 2)])
        self.assert_equal(bl.right_items(), [(2, 'b')])
        self.assert_true('b' in bl)
        self.assert_true(2 in bl)
        self.assert_equal(bl['b'], 2)
        self.assert_equal(bl[2], 'b')
        self.assert_equal(bl.get('b'), 2)
        self.assert_equal(bl.get(2), 'b')
        self.assert_true(bl.get('c') is None)


