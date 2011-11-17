"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 18, 2011.
"""

from everest.testing import Pep8CompliantTestCase
from everest.utils import classproperty
from everest.utils import get_traceback

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
