"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 18, 2011.
"""
from everest.testing import Pep8CompliantTestCase
from everest.utils import BidirectionalLookup
from everest.utils import WeakList
from everest.utils import classproperty
from everest.utils import get_traceback
from everest.utils import id_generator
import random

__docformat__ = 'reStructuredText en'
__all__ = ['UtilsTestCase',
           ]


class UtilsTestCase(Pep8CompliantTestCase):

    def test_id_generator(self):
        # Initialize with start value.
        idgen = id_generator(3)
        self.assert_equal(idgen.next(), 3)
        self.assert_equal(idgen.next(), 4)
        # Push ID to higher value.
        idgen.send(5)
        self.assert_equal(idgen.next(), 6)
        self.assert_equal(idgen.next(), 7)
        # ID values must increase monotonically.
        self.assert_raises(ValueError, idgen.send, 6)

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
        self.assert_is_none(bl.get('not there'))
        self.assert_raises(ValueError, bl.__setitem__, 2, 'c')
        self.assert_raises(ValueError, bl.__setitem__, 0, 'b')
        self.assert_equal(bl.pop_left('not there', 5), 5)
        self.assert_equal(bl.pop_right('not there', 5), 5)
        bl['c'] = 2
        self.assert_true(2 in bl)
        self.assert_false('b' in bl)
        bl['c'] = 1
        self.assert_true(1 in bl)
        self.assert_false(2 in bl)
        bl['x'] = 3
        bl['y'] = 4
        self.assert_true('x' in bl)
        self.assert_true(4 in bl)
        del bl['x']
        del bl[4]
        self.assert_raises(KeyError, bl.__delitem__, 'x')
        self.assert_false('x' in bl)
        self.assert_false(4 in bl)
        bl.clear()
        self.assert_equal(len(bl.left_keys()), 0)
        self.assert_equal(len(bl.right_keys()), 0)

    def test_weaklist(self):
        class _X(object):
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
        # __len__() and deleting items through deleting the held items.
        self.assertEqual(len(weak_list), 6)
        del obj_b
        self.assertEqual(len(weak_list), 3)
        # "in" operation.
        self.assertEqual(obj_a in weak_list, True)
        # iteration.
        item = None
        count = 0
        for item in weak_list:
            count += 1
        self.assertEqual(count, 3)
        del item
        # count().
        self.assertEqual(weak_list.count(obj_a), 3)
        # pop().
        self.assertEqual(weak_list.pop() is obj_a, True)
        # insert() and __getitem__().
        obj_c = C()
        weak_list.insert(2, obj_c)
        self.assertEqual(weak_list[2] is obj_c, True)
        # __setitem__().
        weak_list[0] = obj_c
        self.assertEqual(isinstance(weak_list[0], C), True)
        # slicing.
        weak_list[1:2] = [obj_c]
        self.assertEqual(weak_list[1] is obj_c, True)
        self.assertEqual(weak_list[1:2], [obj_c])
        # index().
        self.assertEqual(weak_list.index(obj_c), 0)
        # .remove().
        weak_list.remove(obj_c)
        self.assertEqual(len(weak_list), 2)
        # extend().
        obj_c1 = C()
        obj_c2 = C()
        obj_c3 = C()
        weak_list.extend([obj_c1, obj_c2, obj_c3])
        self.assertEqual(len(weak_list), 5)
        # sort().
        item = None
        weak_list.sort()
        last_rank = -1
        for item in weak_list:
            self.assertEqual(last_rank <= item.rank, True)
            last_rank = item.rank
        del item
        # append.
        obj_c4 = C()
        weak_list.append(obj_c4)
        self.assert_true(weak_list[-1] is obj_c4)
        # add.
        self.assert_equal(len(weak_list + weak_list), 2 * len(weak_list))
        # clean up.
        del obj_c1, obj_c2, obj_c3, obj_c4
        del obj_a, obj_c
        self.assertEqual(len(weak_list), 0)
