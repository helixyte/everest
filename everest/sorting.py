"""
This file is part of the everest project. 
See LICENSE.txt for licensing, AUTHORS.txt for contributor information.

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

import re
import logging
from pyparsing import ParseException

__docformat__ = 'reStructuredText en'
__all__ = ['Order',
           ]


class Order(object):

    def __init__(self):
        if self.__class__ is Order:
            raise NotImplementedError('Abstract class')

    def accept(self, visitor):
        raise NotImplementedError('Abstract method')

    def eq(self, x, y):
        raise NotImplementedError('Abstract method')

    def lt(self, x, y):
        raise NotImplementedError('Abstract method')

    def ne(self, x, y):
        return not self.eq(x, y)

    def le(self, x, y):
        return self.lt(x, y) or self.eq(x, y)

    def gt(self, x, y):
        return not self.le(x, y)

    def ge(self, x, y):
        return not self.lt(x, y)

    def and_(self, other):
        return ConjuctionOrder(self, other)

    def reverse(self):
        return ReverseOrder(self)


class ObjectOrder(Order): # pylint: disable=W0223

    __attr_name = None

    def __init__(self, attr_name):
        if self.__class__ is ObjectOrder:
            raise NotImplementedError('Abstract class')
        Order.__init__(self)
        self.__attr_name = attr_name

    def __repr__(self):
        str_format = '<%s attr_name: %s>'
        params = (self.__class__.__name__, self.attr_name)
        return str_format % params

    @property
    def attr_name(self):
        return self.__attr_name

    def _get_value(self, obj):
        return getattr(obj, self.attr_name)


class SimpleOrder(ObjectOrder):

    def __init__(self, attr_name):
        ObjectOrder.__init__(self, attr_name)

    def eq(self, x, y):
        return self._get_value(x) == self._get_value(y)

    def lt(self, x, y):
        return self._get_value(x) < self._get_value(y)

    def accept(self, visitor):
        visitor.visit_simple(self)


class ReverseOrder(Order):

    __order = None

    def __init__(self, order):
        Order.__init__(self)
        self.__order = order

    def __repr__(self):
        str_format = '<%s wrapped_order: %s>'
        params = (self.__class__.__name__, self.__order)
        return str_format % params

    def eq(self, x, y):
        return self.__order.eq(y, x)

    def lt(self, x, y):
        return self.__order.lt(y, x)

    def ne(self, x, y):
        return self.__order.ne(y, x)

    def le(self, x, y):
        return self.__order.le(y, x)

    def gt(self, x, y):
        return self.__order.gt(y, x)

    def ge(self, x, y):
        return self.__order.ge(y, x)

    def accept(self, visitor):
        self.__order.accept(visitor)
        visitor.visit_reverse(self)

    @property
    def wrapped(self):
        return self.__order

class NaturalOrder(ObjectOrder):
    """
    See http://www.codinghorror.com/blog/2007/12/sorting-for-humans-natural-sort-order.html
    """

    def __init__(self, attr_name):
        ObjectOrder.__init__(self, attr_name)

    def eq(self, x, y):
        return self._get_natural_value(x) == self._get_natural_value(y)

    def lt(self, x, y):
        return self._get_natural_value(x) < self._get_natural_value(y)

    def accept(self, visitor):
        visitor.visit_natural(self)

    def _get_natural_value(self, obj):
        value = self._get_value(obj)
        if isinstance(value, basestring):
            return [self.__convert(c) for c in re.split(r'([0-9]+)', value)]
        else:
            return value

    def __convert(self, txt):
        return int(txt) if txt.isdigit() else txt


class ConjuctionOrder(Order):

    __left = None
    __right = None

    def __init__(self, left, right):
        Order.__init__(self)
        self.__left = left
        self.__right = right

    def __repr__(self):
        str_format = '<%s left: %s, right: %s>'
        params = (self.__class__.__name__, self.left, self.right)
        return str_format % params

    def eq(self, x, y):
        return self.left.eq(x, y) and self.right.eq(x, y)

    def lt(self, x, y):
        return self.right.lt(x, y) if self.left.eq(x, y) else self.left.lt(x, y)

    @property
    def left(self):
        return self.__left

    @property
    def right(self):
        return self.__right

    def accept(self, visitor):
        self.__left.accept(visitor)
        self.__right.accept(visitor)
        visitor.visit_conjuction(self)


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


class SortOrderDirector(object):
    """
    """

    __builder = None
    __parser = None
    __errors = None
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


class AbstractSortOrderBuilder(object):
    """
    Abstract base class for all Sort Order Builders

    Based on the Builder Design Pattern
    """

    def build_asc(self, attr_name):
        """
        """
        pass

    def build_desc(self, attr_name):
        """
        """
        pass


class SortOrderBuilder(AbstractSortOrderBuilder):
    """
    Concrete builder that creates a sort order
    """

    __order = None
    __factory = None

    def __init__(self, factory):
        AbstractSortOrderBuilder.__init__(self)
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


class AbstractSortOrderFactory(object):
    """
    Abstract base class for all sort order factories
    """

    def __init__(self):
        if self.__class__ is AbstractSortOrderFactory:
            raise NotImplementedError('Abstract class')

    def create_simple(self, attr_name):
        raise NotImplementedError('Abstract method')

    def create_natural(self, attr_name):
        raise NotImplementedError('Abstract method')


class SortOrderFactory(AbstractSortOrderFactory):
    """
    Concrete sort order factory
    """

    def __init__(self):
        AbstractSortOrderFactory.__init__(self)

    def create_simple(self, attr_name):
        return SimpleOrder(attr_name)

    def create_natural(self, attr_name):
        # FIXME: implement. # pylint: disable-msg=W0511
        raise NotImplementedError('TBD')

    def create_starts_with(self, attr_name):
        return NaturalOrder(attr_name)


sort_order_factory = SortOrderFactory()
