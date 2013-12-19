"""
Batch.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 15, 2011.
"""
import math

__docformat__ = "reStructuredText en"
__all__ = ['Batch',
           ]


class Batch(object):
    """
    Helper class to manage batches in a sequence.
    """
    def __init__(self, start, size, total_size):
        """
        :param int start: start index for this batch.
        :param int size: batch size.
        :param int total_size: total size of the batched sequence.
        """
        if start < 0:
            raise ValueError('Batch start must be zero or a positive number.')
        if not size > 0:
            raise ValueError('Batch size must be a positive number.')
        self.start = int(start) // int(size) * int(size)
        self.size = size
        self.total_size = total_size

    @property
    def next(self):
        """
        Returns the next batch for the batched sequence or `None`, if
        this batch is already the last batch.

        :rtype: :class:`Batch` instance or `None`.
        """
        if self.start + self.size > self.total_size:
            result = None
        else:
            result = Batch(self.start + self.size, self.size, self.total_size)
        return result

    @property
    def previous(self):
        """
        Returns the previous batch for the batched sequence or `None`, if
        this batch is already the first batch.

        :rtype: :class:`Batch` instance or `None`.
        """
        if self.start - self.size < 0:
            result = None
        else:
            result = Batch(self.start - self.size, self.size, self.total_size)
        return result

    @property
    def first(self):
        """
        Returns the first batch for the batched sequence.

        :rtype: :class:`Batch` instance.
        """
        return Batch(0, self.size, self.total_size)

    @property
    def last(self):
        """
        Returns the last batch for the batched sequence.

        :rtype: :class:`Batch` instance.
        """
        start = max(self.number - 1, 0) * self.size
        return Batch(start, self.size, self.total_size)

    @property
    def number(self):
        """
        Returns the number of batches the batched sequence contains.

        :rtype: integer.
        """
        return int(math.ceil(self.total_size / float(self.size)))

    @property
    def index(self):
        """
        Returns the index of this batch in the batched sequence.

        :rtype: integer
        """
        return int(self.start / self.size)
