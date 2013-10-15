"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 16, 2013.
"""

__docformat__ = 'reStructuredText en'
__all__ = ['TraversalPath',
           'TraversalPathNode',
           ]


class TraversalPathNode(object):
    """
    Value object representing a node in a traversal path.
    """
    def __init__(self, proxy, attribute, relation_operation):
        """
        :param proxy: Data traversal proxy for this node.
        :param attribute: Resource attribute for this node.
        :param relation_operation: Relation operation for this node. One of
          the constants defined in
          :class:`everest.constants.RELATION_OPERATIONS`.
        """
        self.proxy = proxy
        self.attribute = attribute
        self.relation_operation = relation_operation


class TraversalPath(object):
    """
    Value object tracking a path taken by a data tree traverser.
    """
    def __init__(self, nodes=None):
        if nodes is None:
            nodes = []
        self.nodes = nodes

    def push(self, proxy, attribute, relation_operation):
        """
        Adds a new :class:`TraversalPathNode` constructed from the given
        arguments to this traversal path.
        """
        node = TraversalPathNode(proxy, attribute, relation_operation)
        self.nodes.append(node)

    def pop(self):
        """
        Removes the last traversal path node from this traversal path.
        """
        self.nodes.pop()

    def __len__(self):
        return len(self.nodes)

    def clone(self):
        """
        Returns a copy of this traversal path.
        """
        return TraversalPath(self.nodes[:])

    @property
    def parent(self):
        """
        Returns the proxy from the last node visited on the path, or `None`,
        if no node has been visited yet.
        """
        if len(self.nodes) > 0:
            parent = self.nodes[-1].proxy
        else:
            parent = None
        return parent

    @property
    def relation_operation(self):
        """
        Returns the relation operation from the last node visited on the
        path, or `None`, if no node has been visited yet.
        """
        if len(self.nodes) > 0:
            rel_op = self.nodes[-1].relation_operation
        else:
            rel_op = None
        return rel_op
