"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 21, 2013.
"""
from everest.testing import Pep8CompliantTestCase
from everest.traversalpath import TraversalPath

__docformat__ = 'reStructuredText en'
__all__ = ['TraversalPathTestCase',
           ]


class TraversalPathTestCase(Pep8CompliantTestCase):
    def test_basics(self):
        tp = TraversalPath()
        self.assert_equal(len(tp), 0)
        self.assert_is_none(tp.parent)
        self.assert_is_none(tp.relation_operation)
        parent = 'proxy'
        attr = 'attribute'
        key = ('source', 'target')
        rel_op = 'relation_operation'
        tp.push(parent, key, attr, rel_op)
        self.assert_equal(len(tp), 1)
        self.assert_true(key in tp)
        self.assert_equal(tp.parent, parent)
        self.assert_equal(tp.relation_operation, rel_op)
        tp.pop()
        self.assert_equal(len(tp), 0)
        self.assert_false(key in tp)
