"""
Unit tests for operators.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Sep 7, 2012.
"""
from everest.querying.operators import BinaryOperator
from everest.querying.operators import NullaryOperator
from everest.querying.operators import UnaryOperator
from everest.testing import Pep8CompliantTestCase

__docformat__ = 'reStructuredText en'
__all__ = ['OperatorTestCase',
           ]


class OperatorTestCase(Pep8CompliantTestCase):
    def test_arity(self):
        self.assert_equal(NullaryOperator.arity, 0)
        self.assert_equal(UnaryOperator.arity, 1)
        self.assert_equal(BinaryOperator.arity, 2)

    def test_derived(self):
        class MyNullaryOperator(NullaryOperator):
            @staticmethod
            def apply():
                return True
        self.assert_true(MyNullaryOperator.apply())
