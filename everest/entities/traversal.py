"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 8, 2013.
"""
from everest.attributes import is_terminal_attribute
from everest.constants import CASCADES
from everest.constants import DomainAttributeKinds
from everest.constants import ResourceAttributeKinds
from everest.constants import ResourceKinds
from everest.entities.attributes import \
                        get_domain_class_domain_attribute_iterator
from everest.entities.interfaces import IAggregate
from everest.entities.interfaces import IEntity
from everest.entities.utils import get_entity_class
from everest.repositories.state import EntityStateManager
from everest.representers.interfaces import ICollectionDataElement
from everest.representers.interfaces import ILinkedDataElement
from everest.representers.interfaces import IMemberDataElement
from everest.resources.attributes import get_resource_class_attribute_iterator
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.url import is_url
from everest.utils import get_nested_attribute
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from everest.resources.interfaces import IResource
from everest.resources.utils import get_root_collection
from everest.entities.utils import get_root_aggregate

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


class TRAVERSAL_DATA_KINDS(object):
    ONE = 'ONE'
    MANY = 'MANY'


class TraversalImplementation(object):
    def __init__(self, root, accessor):
        """
        :param root: root of the data tree to traverse.
        :type root: entity, resource, or data element.
        """
        self.root = root
        self.accessor = accessor
        self.__traversed = set()

    def get_iterator(self, data):
        """
        Returns an element iterator for the given sequence (source) data.
        """
        raise NotImplementedError('Abstract method.')

    def get_attribute_value(self, data, attribute):
        """
        Returns the value of the given attribute for the given (source)
        data.
        """
        raise NotImplementedError('Abstract method.')

    def get_attribute_iterator(self, data):
        """
        Returns an attribute iterator for the given (source) data.
        """
        raise NotImplementedError('Abstract method.')

    def get_data_kind(self, attribute, data):
        """
        Determines the traversal data kind for the given attribute and data.
        """
        raise NotImplementedError('Abstract method.')

    def do_traverse(self, attribute, data):
        """
        Checks if the given combination of attribute and data object should
        be traversed.
        """
        raise NotImplementedError('Abstract method.')

    def get_matching(self, attribute, data):
        """
        Looks up matching (target) data for the given (source) data.
        """
        raise NotImplementedError('Abstract method.')

    def _mark_as_traversed(self, key):
        """
        Marks the given key as visited.

        Returns a Boolean indicating if the key had already been visited
        before.
        """
        was_traversed_before = key in self.__traversed
        if not was_traversed_before:
            self.__traversed.add(key)
        return was_traversed_before


class DomainTraversalImplementation(TraversalImplementation):
    def get_iterator(self, data):
        return iter(data)

    def get_attribute_value(self, data, attribute):
        return get_nested_attribute(data, attribute.entity_attr)

    def do_traverse(self, attribute, data):
        return not self._mark_as_traversed(data)

    def get_attribute_iterator(self, data):
        for attr in get_domain_class_domain_attribute_iterator(data):
            if attr.entity_attr is None:
                continue
            yield attr

    def get_data_kind(self, attribute, data):
        if not attribute is None:
            if attribute.kind == DomainAttributeKinds.ENTITY:
                kind = TRAVERSAL_DATA_KINDS.ONE
            elif attribute.kind == DomainAttributeKinds.AGGREGATE:
                kind = TRAVERSAL_DATA_KINDS.MANY
            else:
                raise ValueError('Can only traverse objects for non-terminal '
                                 'domain attributes.')
        else:
            # For the root node, we use the provided interface.
            provided = provided_by(data)
            if IEntity in provided:
                kind = TRAVERSAL_DATA_KINDS.ONE
            elif IAggregate in provided:
                kind = TRAVERSAL_DATA_KINDS.MANY
            else:
                raise ValueError('Can only traverse domain objects that '
                                 'provide IEntity or IAggregate.')
        return kind

    def get_matching(self, attribute, data):
        if not attribute is None:
            agg = self.accessor.get_root_aggregate(attribute.attr_type)
        else:
            agg = self.accessor
        return agg.get_by_id(data.id)


class ResourceTraversalImplementation(TraversalImplementation):
    def get_iterator(self, data):
        return iter(data)

    def get_attribute_value(self, data, attribute):
        return getattr(data, attribute.name)

    def get_attribute_iterator(self, data):
        return get_resource_class_attribute_iterator(data)

    def get_data_kind(self, attribute, data):
        if not attribute is None:
            if attribute.kind == ResourceAttributeKinds.MEMBER:
                kind = TRAVERSAL_DATA_KINDS.ONE
            elif attribute.kind == ResourceAttributeKinds.COLLECTION:
                kind = TRAVERSAL_DATA_KINDS.MANY
            else:
                raise ValueError('Can only traverse objects for non-terminal '
                                 'resource attributes.')
        else:
            # For the root node, we use the provided interface.
            provided = provided_by(data)
            if IMemberResource in provided:
                kind = TRAVERSAL_DATA_KINDS.ONE
            elif ICollectionResource in provided:
                kind = TRAVERSAL_DATA_KINDS.MANY
            else:
                raise ValueError('Can only traverse resource objects that '
                                 'provide IMemberResource or '
                                 'ICollectionResource.')
        return kind

    def do_traverse(self, attribute, data):
        was_traversed_before = self._mark_as_traversed(data)
        if not was_traversed_before:
            if not attribute is None:
                is_rc_attr = attribute.kind != ResourceAttributeKinds.TERMINAL
            else:
                is_rc_attr = IResource in provided_by(data)
            do_trv = is_rc_attr and not is_url(data)
        else:
            do_trv = False
        return do_trv

    def get_matching(self, attribute, data):
        if not attribute is None:
            coll = self.accessor.get_root_collection(attribute.attr_type)
        else:
            coll = self.accessor
        return coll[data.slug]


class DataElementTraversalImplementation(TraversalImplementation):
    def get_iterator(self, data):
        return data.get_members()

    def get_attribute_value(self, data, attribute):
        if is_terminal_attribute(attribute):
            value = data.get_terminal(attribute)
        else:
            value = data.get_nested(attribute)
        return value

    def get_attribute_iterator(self, data):
        rc_cls = data.mapping.mapped_class
        return get_resource_class_attribute_iterator(rc_cls)

    def get_data_kind(self, attribute, data):
        ifcs = provided_by(data)
        if IMemberDataElement in ifcs:
            kind = TRAVERSAL_DATA_KINDS.ONE
        elif ICollectionDataElement in ifcs:
            kind = TRAVERSAL_DATA_KINDS.MANY
        elif ILinkedDataElement in ifcs:
            link_kind = data.get_kind()
            if link_kind == ResourceKinds.MEMBER:
                kind = TRAVERSAL_DATA_KINDS.ONE
            else: # kind == ResourceKinds.COLLECTION
                kind = TRAVERSAL_DATA_KINDS.MANY
        else:
            raise ValueError('Need MEMBER or COLLECTION data element; found '
                             '"%s".' % data)
        return kind

    def do_traverse(self, attribute, data):
        was_traversed_before = self._mark_as_traversed(data)
        if not was_traversed_before:
            do_trv = not ILinkedDataElement in provided_by(data)
        else:
            do_trv = False
        return do_trv

    def get_matching(self, attribute, data):
        # Not needed because we never want to update data element trees.
        raise NotImplementedError('Not implemented.')


class SourceTargetTraverser(object):
    """
    Traverser for synchronous traversal of a source and a target data tree.

    For each data item pair, starting with the root of the source and target
    data tree, iterate over the non-terminal attributes of the associated type
    and obtain the attribute value (child data item) for both the source and
    the target. If the parent source or target data item is `None`, the
    corresponding child data item is also `None`.

    A child nod is only traversed when the parent attribute corresponding
    to it has the ADD (only target found), DELETE (only source found) or
    UPDATE (both source and target found) cascade set.
    """
    def __init__(self, source_implementation, target_implementation):
        self._src_impl = source_implementation
        self._tgt_impl = target_implementation

    @classmethod
    def make_traverser(cls, source_root, target_root=None):
        src_ifcs = provided_by(source_root)
        if IEntity in src_ifcs or IAggregate in src_ifcs:
            src_trv_impl_cls = DomainTraversalImplementation
        elif IMemberResource in src_ifcs or ICollectionResource in src_ifcs:
            src_trv_impl_cls = ResourceTraversalImplementation
        elif IMemberDataElement in src_ifcs \
             or ICollectionDataElement in src_ifcs:
            src_trv_impl_cls = DataElementTraversalImplementation
        else:
            raise ValueError('')
        source_implementation = src_trv_impl_cls(source_root, None)
        tgt_ifcs = provided_by(target_root)
        # Infer the required information from the source.
        if src_trv_impl_cls is DataElementTraversalImplementation:
            tgt_trv_impl_cls = ResourceTraversalImplementation
            if not target_root is None \
               and (not IMemberResource in tgt_ifcs
                    or ICollectionResource in tgt_ifcs):
                raise ValueError('')
            tgt_acc = get_root_collection(source_root.mapped_class)
        elif src_trv_impl_cls is DomainTraversalImplementation:
            if not target_root is None \
               and (not IEntity in tgt_ifcs or IAggregate in tgt_ifcs):
                raise ValueError('')
            tgt_trv_impl_cls = DomainTraversalImplementation
            tgt_acc = get_root_aggregate(source_root)
        elif src_trv_impl_cls is ResourceTraversalImplementation:
            if not target_root is None \
               and (not IMemberResource in tgt_ifcs
                    or ICollectionResource in tgt_ifcs):
                raise ValueError('')
            tgt_trv_impl_cls = ResourceTraversalImplementation
            tgt_acc = get_root_collection(source_root)
        else:
            raise ValueError('')
        target_implementation = tgt_trv_impl_cls(target_root, tgt_acc)
        return SourceTargetTraverser(source_implementation,
                                     target_implementation)

    def run(self, visitor):
        """
        :param visitor: visitor to call with every node in the domain tree.
        :type visitor: subclass of
            :class:`everest.entities.traversal.DomainVisitor`
        """
        kind = self._src_impl.get_data_kind(None, self._src_impl.root)
        if kind == TRAVERSAL_DATA_KINDS.ONE:
            traverse_method = self.traverse_one
        else:
            traverse_method = self.traverse_many
        traverse_method([], None, self._src_impl.root, self._tgt_impl.root,
                        visitor)

    def traverse_one(self, path, attribute, source, target, visitor):
        if not source is None:
            impl = self._src_impl
        else:
            impl = self._tgt_impl
        if impl.do_traverse(attribute, target):
            if target is None and not source.id is None:
                # Look up the target for UPDATE.
                target = self._tgt_impl.get_matching(attribute, source)
                if target is None:
                    raise ValueError('If the source has an ID, a target with '
                                     'the same ID must exist.')
            if not attribute is None:
                trv_rc = attribute.attr_type
            else:
                trv_rc = source
            for attr in impl.get_attribute_iterator(trv_rc):
                if not source is None:
                    source_attr_value = \
                        self._src_impl.get_attribute_value(source, attr)
                else:
                    source_attr_value = None
                if not target is None:
                    target_attr_value = \
                        self._tgt_impl.get_attribute_value(target, attr)
                else:
                    target_attr_value = None
                if source_attr_value is None and target_attr_value is None:
                    # If both source and target have None values, there is
                    # nothing to do.
                    continue
                if target is None:
                    # CREATE
                    do_dispatch = attr.cascade & CASCADES.ADD
                elif source is None:
                    # DELETE
                    do_dispatch = attr.cascade & CASCADES.DELETE
                else:
                    # UPDATE
                    do_dispatch = attr.cascade & CASCADES.UPDATE
                if do_dispatch:
                    data = source_attr_value or target_attr_value
                    kind = impl.get_data_kind(attr, data)
                    path.append((source, target))
                    if kind == TRAVERSAL_DATA_KINDS.ONE:
                        traverse_method = self.traverse_one
                    else:
                        traverse_method = self.traverse_many
                    traverse_method(path[:], attr, source_attr_value,
                                    target_attr_value, visitor)
                    path.pop()
            visitor.visit_one(path, attribute, source, target)

    def traverse_many(self, path, attribute, source_sequence,
                      target_sequence, visitor):
        source_ids = set()
        if not source_sequence is None:
            for source in self._src_impl.get_iterator(source_sequence):
                source_id = source.id
                if not source_id is None:
                    # All not-None IDs must have an existing target: UPDATE
                    source_ids.add(source_id)
                    target = self._tgt_impl.get(attribute, source)
                else:
                    # Target does not exist: ADD
                    target = None
                self.traverse_one(path, attribute, source, target, visitor)
        if not target_sequence is None:
            for target in target_sequence:
                if target.id in source_ids:
                    continue
                # Source does not exist: DELETE
                self.traverse_one(path, attribute, None, target, visitor)
        visitor.visit_many(path, attribute, source_sequence, target_sequence)


class CrudVisitor(object):
    def __init__(self, rc_class,
                 create_callback, update_callback, delete_callback):
        self.__rc_class = rc_class
        self.__create_callback = create_callback
        self.__update_callback = update_callback
        self.__delete_callback = delete_callback
        self.__state_map = {}
        self.__result = None

    def visit_one(self, path, attribute, source_data, target):
        if attribute is None:
            # Visiting the root.
            rc_class = self.__rc_class
            parent = None
        else:
            rc_class = attribute.attr_type
            parent = path[-1][0]
            parent_data = self.__state_map.get(parent)
            if parent_data is None:
                parent_data = self.__state_map.setdefault(parent, {})
        if source_data is None:
            if not parent is None:
                parent_data[attribute] = None
            self.__delete_callback(rc_class, target)
            source = None
        else:
            state_data = EntityStateManager.get_state_data(rc_class,
                                                           source_data)

            if target is None:
                source = self.__create_callback(rc_class, state_data)
            else:
                source = self.__update_callback(rc_class,
                                                source_data, target)
            if not parent is None:
                parent_data[attribute] = state_data
            else:
                self.__result = source

    def visit_many(self, path, attr, source_data, target):
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
