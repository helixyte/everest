"""
This file is part of the everest project. 
See LICENSE.txt for licensing, AUTHORS.txt for contributor information.

Created on May 18, 2011.
"""

from everest.testing import Pep8CompliantTestCase
from everest.utils import WeakList
from everest.utils import classproperty
import random

__docformat__ = 'reStructuredText en'
__all__ = ['WeakListTestCase',
           'UtilsTestCase',
           ]


class UtilsTestCase(Pep8CompliantTestCase):

    def test_classproperty(self):
        class X(object):
            attr = 'myattr'
            @classproperty
            def clsprop(cls): # no self as first arg pylint: disable=E0213
                return cls.attr
        self.assert_equal(X.clsprop, X.attr)


class WeakListTestCase(Pep8CompliantTestCase):
    def test_weak_list(self):
        class _X:
            def __init__(self):
                self.rank = random.randint(0, 20)
            def __lt__(self, other):
                return self.rank < other.rank
            def __le__(self, other):
                return self.rank <= other.rank
            def __eq__(self, other):
                return self.rank == other.rank
            def __ne__(self, other):
                return self.rank != other.rank
            def __gt__(self, other):
                return self.rank > other.rank
            def __ge__(self, other):
                return self.rank >= other.rank
            def __hash__(self):
                return id(self)
        class A(_X):
            pass
        class B(_X):
            pass
        class C(_X):
            pass
        obj_a = A()
        obj_b = B()
        weak_list = WeakList([obj_a, obj_b, obj_a, obj_b, obj_a, obj_b])
        # __len__() and deleting items through deleting the held items:
        self.assert_equal(len(weak_list), 6)
        del obj_b
        self.assert_equal(len(weak_list), 3)
        # "in" operation:
        self.assert_equal(obj_a in weak_list, True)
        # iteration:
        count = 0
        item = None
        for item in weak_list:
            count += 1
        self.assert_equal(count, 3)
        del item
        # .count():
        self.assert_equal(weak_list.count(obj_a), 3)
        # .pop():
        self.assert_equal(weak_list.pop() is obj_a, True)
        # .insert() and .__getitem__():
        obj_c = C()
        weak_list.insert(2, obj_c)
        self.assert_equal(weak_list[2] is obj_c, True)
        # .__setitem__():
        weak_list[0] = obj_c
        self.assert_equal(isinstance(weak_list[0], C), True)
        # slicing:
        weak_list[1:2] = [obj_c]
        self.assert_equal(weak_list[1] is obj_c, True)
        self.assert_equal(weak_list[1:2], [obj_c])
        # .index():
        self.assert_equal(weak_list.index(obj_c), 0)
        # .remove():
        weak_list.remove(obj_c)
        self.assert_equal(len(weak_list), 2)
        # .extend():
        obj_c1 = C()
        obj_c2 = C()
        obj_c3 = C()
        weak_list.extend([obj_c1, obj_c2, obj_c3])
        self.assert_equal(len(weak_list), 5)
        # .sort():
        weak_list.sort()
        last_rank = -1
        item = None
        for item in weak_list:
            self.assert_equal(last_rank <= item.rank, True)
            last_rank = item.rank
        del item
        # clean up:
        del obj_c1, obj_c2, obj_c3
        del obj_a, obj_c
        self.assert_equal(len(weak_list), 0)
