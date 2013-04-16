"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 8, 2013.
"""
from everest.constants import CASCADES
from everest.constants import DomainAttributeKinds
from everest.entities.attributes import get_domain_class_domain_attribute_iterator
from everest.entities.interfaces import IAggregate
from everest.entities.interfaces import IEntity
from everest.entities.utils import get_entity_class
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['AddingDomainVisitor',
           'DomainTreeTraverser',
           'DomainVisitor',
           'RemovingDomainVisitor',
           ]


class DomainTreeTraverser(object):
    """
    Traverser for a tree of domain objects.
    """
    def __init__(self, root):
        self.__root = root
        self.__traversed = set()

    def run(self, visitor):
        """
        Traverses the tree with the given visitor.
        
        :param visitor: visitor to call with every node in the domain tree.
        :type visitor: subclass of
            :class:`everest.entities.traversal.DomainVisitor`
        """
        provided = provided_by(self.__root)
        if IEntity in provided:
            self._traverse_entity([], None, self.__root, visitor)
        elif IAggregate in provided:
            self._traverse_aggregate([], None, self.__root, visitor)
        else:
            raise ValueError('Can only traverse domain objects that '
                             'provide IEntity or IAggregate.')

    def _dispatch(self, path, attr, domain_obj, visitor):
        #: Dispatches the appropriate _traverse_* operation for the given
        #: combination of path, domain attribute, and domain object.
        if attr.kind == DomainAttributeKinds.ENTITY:
            self._traverse_entity(path, attr, domain_obj, visitor)
        elif attr.kind == DomainAttributeKinds.AGGREGATE:
            self._traverse_aggregate(path, attr, domain_obj, visitor)
        else:
            raise ValueError('Can only traverse objects for non-terminal '
                             'domain attributes.')

    def _traverse_entity(self, path, attribute, entity, visitor):
        #: Traverses the given combination of path, domain attribute, and
        #: entity with the given visitor.
        if not entity in self.__traversed:
            self.__traversed.add(entity)
            if not attribute is None:
                ent_cls = get_entity_class(attribute.attr_type)
            else:
                ent_cls = get_entity_class(entity)
            for attr in get_domain_class_domain_attribute_iterator(ent_cls):
                if attr.entity_attr is None:
                    continue
                value = getattr(entity, attr.entity_attr)
                if value is None:
                    continue
                path.append(entity)
                self._dispatch(path, attr, value, visitor)
                path.pop()
            visitor.visit_entity(path, attribute, entity)

    def _traverse_aggregate(self, path, attribute, aggregate, visitor):
        #: Traverses the given combination of path, domain attribute, and
        #: aggregate with the given visitor.
        for ent in aggregate:
            self._traverse_entity(path, attribute, ent, visitor)
        visitor.visit_aggregate(path, attribute, aggregate)


class DomainVisitor(object):
    """
    Abstract base class for domain object visitors.
    """
    def visit_entity(self, entity, path, attr):
        """
        Visits the given entity, path, and attribute combination.

        :param entity: entity to visit.
        :type entity: object implementing
            :class:`everest.entities.interfaces.IEntity`
        :param list path: lineage (parents) of the entity.
        :param attr: domain attribute
        :type attr: instance of
            :class:`everest.entities.attributes.attribute_base`
        """
        raise NotImplementedError('Abstract method.')

    def visit_aggregate(self, aggregate, path, attr):
        """
        Visits the given aggregate, path, and attribute combination.

        :param entity: aggregate to visit.
        :type entity: object implementing
            :class:`everest.entities.interfaces.IAggregate`
        :param list path: lineage (parents) of the aggregate.
        :param attr: domain attribute
        :type attr: instance of
            :class:`everest.entities.attributes.attribute_base`
        """
        raise NotImplementedError('Abstract method.')


class AddingDomainVisitor(DomainVisitor):
    """
    A domain object visitor that adds entities to a session.
    """
    def __init__(self, aggregate, session):
        self.__aggregate = aggregate
        self.__session = session

    def visit_entity(self, path, attr, entity):
        if attr is None:
            # Visiting the root.
            if not entity in self.__session:
                self.__session.add(get_entity_class(entity), entity)
        elif attr.cascade & CASCADES.ADD:
            ent_cls = get_entity_class(attr.attr_type)
            rel = attr.make_relationship(path[-1])
            rel.add(entity)
            if not entity in self.__session:
                if not entity.id is None:
                    root_agg = self.__aggregate.get_root_aggregate(
                                                        attr.attr_type)
                    do_add = root_agg.get_by_id(entity.id) is None
                else:
                    do_add = True
                if do_add:
                    self.__session.add(ent_cls, entity)

    def visit_aggregate(self, path, attr, aggregate):
        pass


class RemovingDomainVisitor(DomainVisitor):
    """
    A domain object visitor that remove entities from a session.
    """
    def __init__(self, aggregate, session):
        self.__aggregate = aggregate
        self.__session = session

    def visit_entity(self, path, attr, entity):
        if attr is None:
            # Visiting the root.
            self.__session.remove(get_entity_class(entity), entity)
        elif attr.cascade & CASCADES.DELETE:
            ent_cls = get_entity_class(attr.attr_type)
            root_agg = self.__aggregate.get_root_aggregate(attr.attr_type)
            if not root_agg.get_by_id(entity.id) is None:
                self.__session.remove(ent_cls, entity)
            rel = attr.make_relationship(path[-1])
            rel.remove(entity)

    def visit_aggregate(self, path, attr, aggregate):
        pass
