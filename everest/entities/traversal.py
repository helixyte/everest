"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 8, 2013.
"""
from everest.constants import CASCADES
from everest.constants import DomainAttributeKinds
from everest.entities.attributes import \
                        get_domain_class_domain_attribute_iterator
from everest.entities.interfaces import IAggregate
from everest.entities.interfaces import IEntity
from everest.entities.utils import get_entity_class
from everest.utils import get_nested_attribute
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from everest.exceptions import NoResultsException
from everest.repositories.state import EntityStateManager

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

    A child node is only traversed when the parent attribute corresponding
    to it has the ADD (only target node found), DELETE (only source node
    found) or UPDATE (both source and target nodes found) cascade set.
    """
    def __init__(self, session, source_root, target_root):
        self.__sess = session
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
            if not getattr(source_entity, 'id', None) is None:
                # If we find a target here: UPDATE else: CREATE
                target_entity = self.__query_by_id(ent_cls, source_entity.id)
            for attr in get_domain_class_domain_attribute_iterator(ent_cls):
                if attr.entity_attr is None:
                    continue
                if not source_entity is None:
                    source_attr_value = \
                        get_nested_attribute(source_entity, attr.entity_attr)
                else:
                    source_attr_value = None
                if not target_entity is None:
                    target_attr_value = \
                        get_nested_attribute(target_entity, attr.entity_attr)
                else:
                    target_attr_value = None
                if source_attr_value is None and target_attr_value is None:
                    # If both source and target have None values, there is
                    # nothing to do.
                    continue
                if target_entity is None:
                    # CREATE
                    do_dispatch = attr.cascade & CASCADES.ADD
                elif source_entity is None:
                    # DELETE
                    do_dispatch = attr.cascade & CASCADES.DELETE
                else:
                    # UPDATE
                    do_dispatch = source_attr_value != target_attr_value \
                                  and attr.cascade & CASCADES.UPDATE
                if do_dispatch:
                    path.append((source_entity, target_entity))
                    self._dispatch(path, attr, source_attr_value,
                                   target_attr_value, visitor)
                    path.pop()
            visitor.visit_entity(path, attribute, source_entity,
                                 target_entity)

    def _traverse_aggregate(self, path, attribute, source_aggregate,
                            target_aggregate, visitor):
        source_ids = set()
        if not source_aggregate is None:
            for source_entity in source_aggregate:
                source_id = source_entity.id
                target_entity = None
                if not source_id is None:
                    source_ids.add(source_id)
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

    def __query_by_id(self, entity_class, entity_id):
        ent = self.__sess.get_by_id(entity_class, entity_id)
        if ent is None:
            try:
                ent = \
                 self.__sess.query(entity_class).filter_by(id=entity_id).one()
            except NoResultsException:
                pass
        return ent


class CrudDomainVisitor(object):
    def __init__(self, rc_class, session_proxy):
        self.__rc_class = rc_class
        self.__session_proxy = session_proxy
        self.__state_map = {}
        self.__result = None

    def visit_entity(self, path, attribute, source_data, target):
        if attribute is None:
            # Visiting the root.
            rc_class = self.__rc_class
            parent = None
        else:
            rc_class = attribute.attr_type
            parent = path[-1][0]
            parent_data = self.__state_map.setdefault(parent, {}).get(parent)
        if source_data is None:
            if not parent is None:
                parent_data[attribute] = None
            self.__session_proxy.remove(rc_class, target)
            source = None
        else:
            state_data = EntityStateManager.get_state_data(rc_class,
                                                           source_data)

            if target is None:
                source = self.__session_proxy.create(rc_class, state_data)
                self.__session_proxy.add(rc_class, source)
            else:
                source = self.__session_proxy.update(rc_class,
                                                     source_data, target)
            if not parent is None:
                parent_data[attribute] = state_data
            else:
                self.__result = source

    def visit_aggregate(self, path, attr, source_aggregate, target_aggregate):
        pass

    @property
    def result(self):
        return self.__result

#    def __create(self, entity_class, entity, relationship=None):
#                if not entity.id is None:
#                    root_agg = self.__agg_fac(entity_class)
#                    do_add = root_agg.get_by_id(entity.id) is None
#                else:
#                    do_add = True
#                if do_add:
#                    self.__session.add(entity_class, entity)
#
#    def __update(self, entity_class, source_entity, target_entity):
#        for attr in get_domain_class_terminal_attribute_iterator(entity_class):
#            source_value = get_nested_attribute(source_entity,
#                                                attr.entity_attr)
#            target_value = get_nested_attribute(target_entity,
#                                                attr.entity_attr)
#            if target_value != source_value:
#                set_nested_attribute(target_entity, attr.entity_attr,
#                                     source_value)
#
#    def __delete(self, entity_class, entity, relationship=None):
#        if not relationship is None:
#            # Visiting the root.
#            self.__remove_callback(entity_class, entity)
#        self.__remove_callback(entity_class, entity)
