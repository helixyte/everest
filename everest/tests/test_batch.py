"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 18, 2011.
"""
import pytest

from everest.batch import Batch


__docformat__ = 'reStructuredText en'
__all__ = ['TestBatch',
           ]


class TestBatch(object):
    @pytest.mark.parametrize('batch_options',
                             [dict(size=100)])
    def test_basics(self, batch_options):
        btch = self._make_batch(**batch_options)
        assert btch.number == 10
        for idx in range(10):
            assert btch.index == idx
            assert btch.start == idx * 100
            if idx > 0:
                assert btch.previous.start == btch.start - btch.size
            if idx < 9:
                btch = btch.next
        assert btch.index == 9

    @pytest.mark.parametrize('batch_options',
                             [dict(size=300)])
    def test_batch_last(self, batch_options):
        btch = self._make_batch(**batch_options)
        assert btch.number == 4
        assert btch.last.start == 900

    @pytest.mark.parametrize('batch_options',
                             [dict(start=199, size=100)])
    def test_odd_start(self, batch_options):
        btch = self._make_batch(**batch_options)
        assert btch.start == 100

    @pytest.mark.parametrize('batch_options',
                             [dict(start=0, size=-10)])
    def test_invalid_size(self, batch_options):
        with pytest.raises(ValueError):
            self._make_batch(**batch_options)

    @pytest.mark.parametrize('batch_options',
                             [dict(start=-1)])
    def test_invalid_start(self, batch_options):
        with pytest.raises(ValueError):
            self._make_batch(**batch_options)

    @pytest.mark.parametrize('batch_options',
                             [dict(start=0, size=20, total_size=0)])
    def test_empty_batch(self, batch_options):
        btch = self._make_batch(**batch_options)
        assert btch.first.start == 0
        assert btch.last.start == 0
        assert btch.next is None
        assert btch.previous is None

    @pytest.mark.parametrize('batch_options',
                             [dict(start=100.)])
    def test_float_start(self, batch_options):
        btch = self._make_batch(**batch_options)
        assert isinstance(btch.index, int)

    def _make_batch(self, start=0, size=100, total_size=1000):
        return Batch(start, size, total_size)
