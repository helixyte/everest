"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 18, 2011.
"""

from everest.batch import Batch
from everest.testing import Pep8CompliantTestCase

__docformat__ = 'reStructuredText en'
__all__ = ['BatchTestCase',
           ]


class BatchTestCase(Pep8CompliantTestCase):

    def set_up(self):
        self.data = range(1000)

    def test_basics(self):
        btch = self._make_batch(size=100)
        self.assert_equal(btch.number, 10)
        for idx in range(10):
            self.assert_equal(btch.index, idx)
            self.assert_equal(btch.start, idx * 100)
            if idx < 9:
                btch = btch.next
        self.assert_equal(btch.index, 9)

    def test_batch_last(self):
        btch = self._make_batch(size=300)
        self.assert_equal(btch.number, 4)
        self.assert_equal(btch.last.start, 900)

    def test_odd_start(self):
        btch = self._make_batch(start=199, size=100)
        self.assert_equal(btch.start, 100)

    def test_invalid_start(self):
        self.assert_raises(ValueError,
                           self._make_batch,
                           - 1)

    def test_empty_batch(self):
        btch = self._make_batch(0, 20, 0)
        self.assert_equal(btch.first.start, 0)
        self.assert_equal(btch.last.start, 0)
        self.assert_equal(btch.next, None)
        self.assert_equal(btch.previous, None)

    def test_float_start(self):
        btch = self._make_batch(start=100.)
        self.assert_true(isinstance(btch.index, int))

    def _make_batch(self, start=0, size=100, total_size=1000):
        return Batch(start, size, total_size)
