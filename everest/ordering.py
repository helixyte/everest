"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

In 1985, Susan Merritt proposed a new taxonomy for comparison-based sorting
algorithms. At the heart of Merritt's thesis is the principle of divide and
conquer. Merritt's thesis is potentially a very powerful method for studying
and understanding sorting. However, the paper did not offer any concrete
implementation of the proposed taxonomy. The following is an object-oriented
formulation and implementation of Merritt's taxonomy, based on Design Patterns
for Sorting presented at http://cnx.org/content/m17309/latest/

See also:

D. Nguyen and S. Wong, "Design Patterns for Sorting," SIGCSE Bulletin 33:1,
    March 2001, 263-267.

S. Merritt, "An Inverted Taxonomy of Sorting Algorithms" Comm. of the ACM,
    Jan. 1985, Volume 28, Number 1, pp. 96-99.

Created on Jul 5, 2011.
"""

from everest.interfaces import IOrderSpecificationBuilder
from everest.interfaces import IOrderSpecificationDirector
from pyparsing import ParseException
from zope.interface import implements # pylint: disable=E0611,F0401
import logging

__docformat__ = 'reStructuredText en'
__all__ = ['BubbleSorter',
           'OrderSpecificationBuilder',
           'OrderSpecificationDirector',
           'Sorter',
           'SorterTemplate',
           ]


class Sorter(object):

    _order = None

    def __init__(self, order):
        if self.__class__ is Sorter:
            raise NotImplementedError('Abstract class')
        self._order = order

    def sort(self, lst, lo=None, hi=None):
        raise NotImplementedError('Abstract method')

    def set_order(self, order):
        self._order = order


class SorterTemplate(Sorter):

    def __init__(self, order):
        if self.__class__ is SorterTemplate:
            raise NotImplementedError('Abstract class')
        Sorter.__init__(self, order)

    def sort(self, lst, lo=None, hi=None):
        lo = 0 if lo is None else lo
        hi = (len(lst) - 1) if hi is None else hi
        if lo < hi:
            s = self._split(lst, lo, hi)
            self.sort(lst, lo, s - 1)
            self.sort(lst, s, hi)
            self._join(lst, lo, s, hi)

    def _split(self, lst, lo, hi):
        raise NotImplementedError('Abstract method')

    def _join(self, lst, lo, s, hi):
        raise NotImplementedError('Abstract method')


class BubbleSorter(SorterTemplate):

    def __init__(self, order):
        SorterTemplate.__init__(self, order)

    def _split(self, lst, lo, hi):
        j = hi
        while lo < j:
            if self._order.lt(lst[j], lst[j - 1]):
                temp = lst[j]
                lst[j] = lst[j - 1]
                lst[j - 1] = temp
            j -= 1
        return lo + 1

    def _join(self, lst, low_index, split_index, high_index):
        pass


class OrderSpecificationDirector(object):
    """
    """

    implements(IOrderSpecificationDirector)

    __logger = logging.getLogger(__name__)

    def __init__(self, parser, builder):
        self.__parser = parser
        self.__builder = builder
        self.__errors = []

    def construct(self, order):
        try:
            self.__logger.debug('Sort order received: %s' % order)
            result = self.__parser(order)
        except ParseException, e:
            # FIXME: show better error messages # pylint: disable=W0511
            self.__errors.append('Sort order parameters have errors. %s' % e)
        else:
            self.__process_order(result.order)

    def has_errors(self):
        return len(self.__errors) > 0

    def get_errors(self):
        return self.__errors[:]

    def _format_identifier(self, string):
        return string.replace('-', '_')

    def __process_order(self, order):
        for sort_order in order:
            name, oper = sort_order
            name = self._format_identifier(name)
            command = getattr(self.__builder, 'build_%s' % oper)
            command(name)


class OrderSpecificationBuilder(object):
    """
    Order specification builder.
    """

    implements(IOrderSpecificationBuilder)

    def __init__(self, factory):
        self.__order = None
        self.__factory = factory

    def build_asc(self, attr_name):
        self.__append_order(
            self.__factory.create_simple(attr_name)
            )

    def build_desc(self, attr_name):
        self.__append_order(
            self.__factory.create_simple(attr_name).reverse()
            )

    def get_sort_order(self):
        return self.__order

    def __append_order(self, new_order):
        if self.__order is None:
            self.__order = new_order
        else:
            self.__order = self.__order.and_(new_order)
