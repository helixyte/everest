"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 8, 2013.
"""
from everest.constants import CASCADES
from everest.constants import DomainAttributeKinds
from everest.entities.attributes import \
                        get_domain_class_domain_attribute_iterator
from everest.entities.attributes import \
                        get_domain_class_terminal_attribute_iterator
from everest.entities.interfaces import IAggregate
from everest.entities.interfaces import IEntity
from everest.entities.utils import get_entity_class
from everest.utils import get_nested_attribute
from everest.utils import set_nested_attribute
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
    
    The traverser makes sure no node is visited twice.
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
                value = get_nested_attribute(entity, attr.entity_attr)
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


class SourceTargetTraverser(object):
    """
    Traverser for synchronous traversal of a source and a target node tree.
    
    For each node pair, starting with the root source and target nodes, iterate
    over the non-terminal attributes of the associated type and obtain the
    attribute value (child node) for both the source and the target node. If
    the parent source or target node is `None`, the corresponding child node
    is also `None`. 
    
    source tree with the given visitor. For each child node
    in the source tree, the corresponding node in the target tree is
    looked up; if it is not found, `None` is used as source node argument
    for the visit. Likewise, for each source node that does not have a
    target node, `None` is used as the target node argument for the visit.
    
    A child node is only traversed when the parent attribute corresponding
    to it has the ADD (only target node found), DELETE (only source node
    found) or UPDATE (both source and target nodes found) cascade set. 
    """
    def __init__(self, aggregate_factory, source_root, target_root):
        self.__agg_fac = aggregate_factory
        self.__source_root = source_root
        self.__target_root = target_root
        self.__traversed = set()

    def run(self, visitor):
        """
        :param visitor: visitor to call with every node in the domain tree.
        :type visitor: subclass of
            :class:`everest.entities.traversal.DomainVisitor`
        """
        provided = provided_by(self.__source_root or self.__target_root)
        if IEntity in provided:
            self._traverse_entity([], None, self.__source_root,
                                  self.__target_root, visitor)
        elif IAggregate in provided:
            self._traverse_aggregate([], None, self.__source_root,
                                     self.__target_root, visitor)
        else:
            raise ValueError('Can only traverse domain objects that '
                             'provide IEntity or IAggregate.')

    def _dispatch(self, path, attribute, source, target, visitor):
        #: Dispatches the appropriate _traverse_* operation for the given
        #: combination of path, domain attribute, and domain object.
        if attribute.kind == DomainAttributeKinds.ENTITY:
            self._traverse_entity(path, attribute, source, target, visitor)
        elif attribute.kind == DomainAttributeKinds.AGGREGATE:
            self._traverse_aggregate(path, attribute, source, target, visitor)
        else:
            raise ValueError('Can only traverse objects for non-terminal '
                             'domain attributes.')

    def _traverse_entity(self, path, attribute, source_entity, target_entity,
                         visitor):
        key = (source_entity, target_entity)
        if not key in self.__traversed:
            self.__traversed.add(key)
            if not attribute is None:
                ent_cls = get_entity_class(attribute.attr_type)
            else:
                ent_cls = get_entity_class(source_entity or target_entity)
            for attr in get_domain_class_domain_attribute_iterator(ent_cls):
                if attr.entity_attr is None:
                    continue
                if not source_entity is None:
                    attr_source = \
                        get_nested_attribute(source_entity, attr.entity_attr)
                else:
                    attr_source = None
                if not target_entity is None:
                    attr_target = \
                        get_nested_attribute(target_entity, attr.entity_attr)
                else:
                    attr_target = None
                if attr_source is None and attr_target is None:
                    # If both source and target have None values, there is
                    # nothing to do.
                    continue
                if target_entity is None:
                    # CREATE
                    do_dispatch = attr.cascade & CASCADES.ADD
                    if do_dispatch and not source_entity.id is None:
                        agg = self.__agg_fac(ent_cls)
                        # if we find a target here: UPDATE else: CREATE
                        target_entity = agg.get_by_id(source_entity.id)
#                        if not target_entity is None and attribute is None:
#                            raise ValueError('ADD entity with ID %s '
#                                             'conflicts with existing '
#                                             'entity.' % target_entity.id)
                elif source_entity is None:
                    # DELETE
                    do_dispatch = attr.cascade & CASCADES.DELETE
#                    if do_dispatch:
#                        agg = self.__agg_fac(ent_cls)
#                        if agg.get_by_id(target_entity.id) is None:
#                            raise ValueError('Can not DELETE non-existing '
#                                             'entity with ID %s.'
#                                             % target_entity.id)
                else:
                    # UPDATE
                    do_dispatch = attr.cascade & CASCADES.UPDATE
                if do_dispatch:
                    path.append((source_entity, target_entity))
                    self._dispatch(path, attr, attr_source, attr_target,
                                   visitor)
                    path.pop()
            visitor.visit_entity(path, attribute, source_entity,
                                 target_entity)

    def _traverse_aggregate(self, path, attribute, source_aggregate,
                            target_aggregate, visitor):
        source_ids = set()
        agg = None
        if not source_aggregate is None:
            for source_entity in source_aggregate:
                source_id = source_entity.id
                if not source_id is None:
                    source_ids.add(source_id)
                    if not target_aggregate is None:
                        if agg is None:
                            ent_cls = get_entity_class(source_entity)
                            agg = self.__agg_fac(ent_cls)
                        # if we find a target here: UPDATE else: CREATE
                        target_entity = agg.get_by_id(source_id)
                    else:
                        # CREATE
                        target_entity = None
                else:
                    # CREATE
                    target_entity = None
                self._traverse_entity(path, attribute, source_entity,
                                      target_entity, visitor)
        if not target_aggregate is None:
            for target_entity in target_aggregate:
                if target_entity.id in source_ids:
                    continue
                # DELETE
                self._traverse_entity(path, attribute, None, target_entity,
                                      visitor)
        visitor.visit_aggregate(path, attribute, source_aggregate,
                                target_aggregate)


class CrudDomainVisitor(object):
    def __init__(self, aggregate_factory, session):
        self.__agg_fac = aggregate_factory
        self.__session = session

    def visit_entity(self, path, attribute, source_entity, target_entity):
        if attribute is None:
            # Visiting the root.
            entity_class = get_entity_class(source_entity or target_entity)
        else:
            entity_class = get_entity_class(attribute.attr_type)
#        if target_entity is None and not source_entity.id is None:
#            # Try to load the target entity if we have an ID.
#            agg = self.__agg_fac(source_entity)
#            target_entity = agg.get_by_id(source_entity.id)
        if source_entity is None or target_entity is None:
            if attribute is None:
                relationship = None
            else:
                if source_entity is None:
                    parent = path[-1][1]
                else:
                    parent = path[-1][0]
                relationship = attribute.make_relationship(parent)
            if target_entity is None:
                self.__create(source_entity, entity_class,
                              relationship=relationship)
            else:
                self.__delete(target_entity, entity_class,
                              relationship=relationship)
        else:
            self.__update(entity_class, source_entity, target_entity)

    def visit_aggregate(self, path, attr, source_aggregate, target_aggregate):
        pass

    def __create(self, entity, entity_class, relationship=None):
        if relationship is None:
            if not entity in self.__session:
                self.__session.add(entity_class, entity)
        else:
            relationship.add(entity)
            if not entity in self.__session:
                if not entity.id is None:
                    root_agg = self.__agg_fac(entity_class)
                    do_add = root_agg.get_by_id(entity.id) is None
                else:
                    do_add = True
                if do_add:
                    self.__session.add(entity_class, entity)

    def __update(self, entity_class, source_entity, target_entity):
        for attr in get_domain_class_terminal_attribute_iterator(entity_class):
            source_value = get_nested_attribute(source_entity,
                                                attr.entity_attr)
            target_value = get_nested_attribute(target_entity,
                                                attr.entity_attr)
            if target_value != source_value:
                set_nested_attribute(target_entity, attr.entity_attr,
                                     source_value)

    def __delete(self, entity, entity_class, relationship=None):
        if relationship is None:
            # Visiting the root.
            self.__session.remove(entity_class, entity)
        else:
            root_agg = self.__agg_fac(entity_class)
            if not root_agg.get_by_id(entity.id) is None:
                self.__session.remove(entity_class, entity)
            relationship.remove(entity)
