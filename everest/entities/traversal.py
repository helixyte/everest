"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 8, 2013.
"""
from everest.attributes import AttributeValueMap
from everest.attributes import get_attribute_cardinality
from everest.attributes import is_terminal_attribute
from everest.constants import CARDINALITY_CONSTANTS
from everest.constants import CASCADES
from everest.constants import DomainAttributeKinds
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
from everest.resources.attributes import \
                    get_resource_class_resource_attribute_iterator
from everest.resources.attributes import get_resource_class_attribute_iterator
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.staging import create_staging_collection
from everest.resources.utils import as_member
from everest.resources.utils import get_resource_class_for_relation
from everest.resources.utils import url_to_resource
from everest.utils import get_nested_attribute
from everest.utils import set_nested_attribute
from pyramid.compat import iteritems_
from pyramid.compat import iterkeys_
from pyramid.compat import itervalues_
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['AddingDomainVisitor',
           'DomainTreeTraverser',
           'DomainVisitor',
           'RemovingDomainVisitor',
           'SourceTargetDataTreeTraverser',
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
        elif attr.cascade & CASCADES.REMOVE:
            ent_cls = get_entity_class(attr.attr_type)
            root_agg = self.__aggregate.get_root_aggregate(attr.attr_type)
            if not root_agg.get_by_id(entity.id) is None:
                self.__session.remove(ent_cls, entity)
            rel = attr.make_relationship(path[-1])
            rel.remove(entity)

    def visit_aggregate(self, path, attr, aggregate):
        pass


class DataTraversalProxy(object):
    """
    Abstract base class for data tree traversal proxies.

    This proxy provides a uniform interface to the elements of data trees
    encountered during tree traversal.
    """
    def __init__(self, data, accessor):
        """
        :param data: root of the data tree to traverse.
        """
        self.cardinality = self._validate_data(data)
        self.data = data
        self._accessor = accessor

    @classmethod
    def make_proxy(cls, data):
        if isinstance(data, AttributeValueMap):
            prx_cls = AttributeValueMapDataTraversalProxy
        else:
            ifcs = provided_by(data)
            if IEntity in ifcs or IAggregate in ifcs:
                prx_cls = DomainDataTraversalProxy
            elif IMemberResource in ifcs or ICollectionResource in ifcs:
                prx_cls = ResourceDataTraversalProxy
            elif IMemberDataElement in ifcs or ICollectionDataElement in ifcs:
                prx_cls = DataElementDataTraversalProxy
            else:
                raise ValueError('Invalid data for traversal proxy "%s".'
                                 % data)
        return prx_cls(data, None)

    def get_id(self):
        """
        Returns the given (source) data ID.
        """
        raise NotImplementedError('Abstract method.')

    def get_value(self, attribute):
        """
        Returns a traversal proxy for the value of the given attribute for
        the given data.
        """
        raise NotImplementedError('Abstract method.')

    def set_value(self, attribute, value):
        """
        Sets the given attribute on the proxied data to the given value.
        """
        raise NotImplementedError('Abstract method.')

    def get_attribute_iterator(self):
        """
        Returns an attribute iterator for the given data.
        """
        raise NotImplementedError('Abstract method.')

    def do_traverse(self, attribute):
        """
        Checks if the given combination of attribute and data object should
        be traversed.
        """
        raise NotImplementedError('Abstract method.')

    def get_matching(self, attribute):
        """
        Looks up matching (target) data for the given (source) data.
        """
        raise NotImplementedError('Abstract method.')

    def get_type(self):
        """
        Returns the type of the proxied data.
        """
        raise NotImplementedError('Abstract method.')

    def as_domain_object(self):
        """
        Returns the proxied data as a domain object.
        """
        raise NotImplementedError('Abstract method.')

    def as_attribute_value_map(self):
        """
        Returns the proxied data as attribute value map.
        """
        raise NotImplementedError('Abstract method.')

    def _validate_data(self, data):
        """
        Validates the data to be proxied.

        :raises ValueError: If validation fails.
        """
        raise NotImplementedError('Abstract method.')

    def as_resource_object(self):
        """
        Returns the proxied data as a resource object.
        """
        domain_obj = self.as_domain_object()
        if self.cardinality == CARDINALITY_CONSTANTS.ONE:
            rc = as_member(domain_obj)
        else:
            rc = create_staging_collection(self.get_type())
            for ent in domain_obj:
                rc.create_member(ent)
        return rc


class DomainDataTraversalProxy(DataTraversalProxy):
    def get_id(self):
        return self.data.id

    def get_value(self, attribute):
        if self.cardinality == CARDINALITY_CONSTANTS:
            attr_val = get_nested_attribute(self.data, attribute.entity_attr)
            val = DomainDataTraversalProxy(attr_val)
        else:
            val = (DomainDataTraversalProxy(ent) for ent in iter(self.data))
        return val

    def set_value(self, attribute, value):
        if self.cardinality == CARDINALITY_CONSTANTS.ONE:
            set_nested_attribute(self.data, attribute, value)
        else:
            self.data.append(value)

    def do_traverse(self, attribute):
        return True

    def get_attribute_iterator(self):
        for attr in get_domain_class_domain_attribute_iterator(self.data):
            if attr.entity_attr is None:
                continue
            yield attr

    def get_matching(self, attribute):
        if not attribute is None:
            agg = self._accessor.get_root_aggregate(attribute.attr_type)
        else:
            agg = self._accessor
        return agg.get_by_id(self.data.id)

    def get_type(self):
        return type(self.data)

    def as_domain_object(self):
        return self.data

    def as_attribute_value_map(self):
        ent_cls = self.get_type()
        if self.cardinality == CARDINALITY_CONSTANTS.ONE:
            av_map = EntityStateManager.get_state_data(ent_cls, self.data)
            av_map['__class__'] = ent_cls
            result = av_map
        else:
            result = []
            for ent in self.data:
                av_map = EntityStateManager.get_state_data(ent_cls, ent)
                av_map['__class__'] = ent_cls
                result.append(av_map)
        return result

    def _validate_data(self, data):
        provided = provided_by(data)
        if IEntity in provided:
            card = CARDINALITY_CONSTANTS.ONE
        elif IAggregate in provided:
            card = CARDINALITY_CONSTANTS.MANY
        else:
            raise ValueError('Expected object providing IEntity or '
                             'IAggregate, found %s.' % data)
        return card


class ResourceDataTraversalProxy(DataTraversalProxy):
    def get_id(self):
        return self.data.id

    def get_value(self, attribute):
        if self.cardinality == CARDINALITY_CONSTANTS.ONE:
            attr_val = get_nested_attribute(self.data, attribute.name)
            val = ResourceDataTraversalProxy(attr_val)
        else:
            val = (ResourceDataTraversalProxy(el) for el in iter(self.data))
        return val

    def set_value(self, attribute, value):
        if self.cardinality == CARDINALITY_CONSTANTS.ONE:
            set_nested_attribute(self.data, attribute, value)
        else:
            self.data.append(value)

    def get_attribute_iterator(self):
        return get_resource_class_resource_attribute_iterator(self.data)

    def do_traverse(self, attribute):
        return True

    def get_matching(self, attribute):
        if not attribute is None:
            coll = self._accessor.get_root_collection(attribute.attr_type)
        else:
            coll = self._accessor
        return coll[self.data.slug]

    def as_domain_object(self):
        if self.cardinality == CARDINALITY_CONSTANTS.ONE:
            domain_obj = self.data.get_entity()
        else:
            domain_obj = [mb.get_entity() for mb in self.data]
        return domain_obj

    def as_attribute_value_map(self):
        if self.cardinality == CARDINALITY_CONSTANTS.ONE:
            av_map = self.__create_av_map(self.data)
            av_map['__class__'] = self.get_type()
            result = av_map
        else:
            result = []
            for mb in self.data:
                av_map = self.__create_av_map(mb)
                av_map['__class__'] = self.get_type()
                result.append(av_map)
        return result

    def __create_av_map(self, data):
        av_map = {}
        for attr in get_resource_class_attribute_iterator(data):
            av_map[attr] = get_nested_attribute(self.data, attr.attr_name)
        return av_map

    def get_type(self):
        return type(self.data)

    def _validate_data(self, data):
        provided = provided_by(data)
        if IMemberResource in provided:
            card = CARDINALITY_CONSTANTS.ONE
        elif ICollectionResource in provided:
            card = CARDINALITY_CONSTANTS.MANY
        else:
            raise ValueError('Expected object providing IMemberResource or '
                             'ICollectionResource, found %s.' % data)
        return card


class AttributeValueMapDataTraversalProxy(DataTraversalProxy):
    def get_id(self):
        return self.data['id']

    def get_value(self, attribute):
        if self.cardinality == CARDINALITY_CONSTANTS.ONE:
            attr_val = self.data[attribute]
            val = AttributeValueMapDataTraversalProxy(attr_val)
        else:
            val = (AttributeValueMapDataTraversalProxy(el)
                   for el in iter(self.data))
        return val

    def set_value(self, attribute, value):
        if self.cardinality == CARDINALITY_CONSTANTS.ONE:
            self.data[attribute] = value
        else:
            self.data.append(value)

    def get_attribute_iterator(self):
        for attr in iterkeys_(self.data):
            if not is_terminal_attribute(attr):
                yield attr

    def do_traverse(self, attribute):
        return True

    def get_matching(self, attribute):
        # Not needed because we never want to update attribute value maps.
        raise NotImplementedError('Not implemented.')

    def get_type(self):
        mb_cls = get_resource_class_for_relation(self.data['__class__'])
        return get_entity_class(mb_cls)

    def as_domain_object(self):
        if self.cardinality == CARDINALITY_CONSTANTS.ONE:
            domain_obj = self.__create_entity(self.data)
        else:
            domain_obj = [self.__create_entity(avm) for avm in self.data]
        return domain_obj

    def as_attribute_value_map(self):
        return self.data

    def _validate_data(self, data):
        if isinstance(data, AttributeValueMap):
            card = CARDINALITY_CONSTANTS.ONE
        elif isinstance(data, list):
            card = CARDINALITY_CONSTANTS.MANY
        else:
            raise ValueError('Expected AttributeValueMap object or list, '
                             'found %s.' % data)
        return card

    def __create_entity(self, attr_value_map):
        init_map = {}
        nested_map = {}
        for attr, value in iteritems_(attr_value_map):
            if attr == '__class__':
                continue
            attr_name = attr.entity_name
            if not '.' in attr_name:
                init_map[attr_name] = value
            else:
                nested_map[attr_name] = value
        entity = self.get_type().create_from_data(init_map)
        for nested_name, nested_value in iteritems_(nested_map):
            set_nested_attribute(entity, nested_name, nested_value)
        return entity


class DataElementDataTraversalProxy(DataTraversalProxy):
    def get_id(self):
        id_attr = self.data.mapping.get_attribute_map()['id']
        return self.data.get_terminal(id_attr)

    def get_value(self, attribute):
        if self.cardinality == CARDINALITY_CONSTANTS.ONE:
            attr_val = self.data.get_nested(attribute)
            val = DataElementDataTraversalProxy(attr_val)
        else:
            val = (DataElementDataTraversalProxy(el)
                   for el in iter(self.data.get_members()))
        return val

    def set_value(self, attribute, value):
        if self.cardinality == CARDINALITY_CONSTANTS.ONE:
            if is_terminal_attribute(attribute):
                self.data.set_terminal(attribute, value)
            else:
                self.data.set_nested(attribute, value)
        else:
            self.data.add_member(value)

    def get_attribute_iterator(self):
        for attr in self.data.mapping.attribute_iterator():
            if not is_terminal_attribute(attr):
                yield attr

    def do_traverse(self, attribute):
        return True

    def get_matching(self, attribute):
        # Not needed because we never want to update data element trees.
        raise NotImplementedError('Not implemented.')

    def get_type(self):
        return self.data.mapping.mapped_class

    def as_domain_object(self):
        if self.cardinality == CARDINALITY_CONSTANTS.ONE:
            domain_obj = self.__create_entity(self.data)
        else:
            domain_obj = [self.__create_entity(d_el)
                          for d_el in self.data.get_members()]
        return domain_obj

    def as_attribute_value_map(self):
        if self.cardinality == CARDINALITY_CONSTANTS.ONE:
            av_map = self.__create_av_map(self.data)
            result = av_map
        else:
            result = []
            for el in self.data.get_members():
                av_map = self.__create_av_map(el)
                result.append(av_map)
        return result

    def _validate_data(self, data):
        ifcs = provided_by(data)
        if IMemberDataElement in ifcs:
            card = CARDINALITY_CONSTANTS.ONE
        elif ICollectionDataElement in ifcs:
            card = CARDINALITY_CONSTANTS.MANY
        elif ILinkedDataElement in ifcs:
            link_kind = self.data.get_kind()
            if link_kind == ResourceKinds.MEMBER:
                card = CARDINALITY_CONSTANTS.ONE
            else: # kind == ResourceKinds.COLLECTION
                card = CARDINALITY_CONSTANTS.MANY
        else:
            raise ValueError('Expected MEMBER or COLLECTION data element; '
                             'found "%s".' % data)
        return card

    def __create_entity(self, data_el):
        if ILinkedDataElement in provided_by(data_el):
            url = data_el.get_url()
            rc = url_to_resource(url)
            entity = rc.get_entity()
        else:
            init_map = {}
            nested_map = {}
            # Update state map with terminal attribute values.
            for attr in data_el.mapping.attribute_iterator():
                if is_terminal_attribute(attr):
                    value = data_el.get_terminal(attr)
                    attr_name = attr.entity_name
                    if not '.' in attr_name:
                        init_map[attr_name] = value
                    else:
                        nested_map[attr_name] = value
            entity = self.get_type().create_from_data(init_map)
            for nested_name, nested_value in iteritems_(nested_map):
                set_nested_attribute(entity, nested_name, nested_value)
        return entity

    def __create_av_map(self, data):
        av_map = {}
        for attr in self.data.mapping.attribute_iterator():
            if is_terminal_attribute(attr):
                av_map[attr] = data.get_terminal(attr)
            else:
                av_map[attr] = data.get_nested(attr)
        return av_map


class SourceTargetDataTreeTraverser(object):
    """
    Traverser for synchronous traversal of a source and a target data tree.

    For each data item pair, starting with the root of the source and target
    data tree, iterate over the non-terminal attributes of the associated type
    and obtain the attribute value (child data item) for both the source and
    the target. If the parent source or target data item is `None`, the
    corresponding child data item is also `None`.

    A child node is traversed along the ADD cascade when only the source
    was found, along the REMOVE cascade when only the target was found, and
    along the UPDATE cascade when both source and target were found. Traversal
    is suppressed when the parent attribute does not have the apprpriate
    cascading flag set.

    When traversing along the ADD or REMOVE cascade, child nodes are only
    traversed when they also amount to an ADD or REMOVE traversal,
    respectively (e.g., an UPDATE inside an ADD or REMOVE is not allowed).
    """
    def __init__(self, source_proxy, target_proxy):
        self._src_prx = source_proxy
        self._tgt_prx = target_proxy
        self.__traversed = set()

    @classmethod
    def make_traverser(cls, source_root, target_root=None):
        if isinstance(source_root, AttributeValueMap) and target_root is None:
            raise ValueError('Must supply a target root when traversing '
                             'with an attribute value map.')
        if source_root is None:
            source_proxy = DataTraversalProxy.make_proxy(source_root)
        else:
            source_proxy = None
        if not target_root is None:
            target_proxy = DataTraversalProxy.make_proxy(target_root)
        else:
            target_proxy = None
        return cls(source_proxy, target_proxy)

    def run(self, visitor):
        """
        :param visitor: visitor to call with every node in the domain tree.
        :type visitor: subclass of
            :class:`everest.entities.traversal.DomainVisitor`
        """
        if not self._src_prx is None:
            card = self._src_prx.cardinality
        else:
            card = self._tgt_prx.cardinality
        if card == CARDINALITY_CONSTANTS.ONE:
            traverse_method = self.traverse_one
        else:
            traverse_method = self.traverse_many
        traverse_method([], None, self._src_prx, self._tgt_prx, visitor)

    def traverse_one(self, path, attribute, source, target, visitor):
        """
        :param source: source data proxy
        :type source: instance of `DataTraversalProxy` or None
        :param target: target data proxy
        :type target: instance of `DataTraversalProxy` or None
        """
        # We do not follow nested UPDATEs unless the current operation is
        # also an UPDATE.
        key = (source.data, target.data)
        was_traversed = key in self.__traversed
        if not was_traversed:
            self.__traversed.add(key)
            if not(target is None and not source.get_id() is None
                   or source is None and target.get_id() is None):
#                # Look up the target for UPDATE.
#                target = self._tgt_prx.get_matching(attribute, source)
#                if target is None:
#                    raise ValueError('If the source has an ID, a target with'
#                                     ' the same ID must exist.')
                prx = source or target
                for attr in prx.get_attribute_iterator():
                    if not source is None:
                        source_attr_proxy = source.get_value(attr)
                    else:
                        source_attr_proxy = None
                    if not target is None:
                        target_attr_proxy = target.get_value(attr)
                    else:
                        target_attr_proxy = None
                    if source_attr_proxy is None and target_attr_proxy is None:
                        # If both source and target have None values, there is
                        # nothing to do.
                        continue
                    if target is None:
                        # CREATE
                        do_dispatch = bool(attr.cascade & CASCADES.ADD)
                    elif source is None:
                        # REMOVE
                        do_dispatch = bool(attr.cascade & CASCADES.REMOVE)
                    else:
                        # UPDATE
                        do_dispatch = bool(attr.cascade & CASCADES.UPDATE)
                    if do_dispatch:
                        card = get_attribute_cardinality(attr)
                        if card == CARDINALITY_CONSTANTS.ONE:
                            traverse_method = self.traverse_one
                        else:
                            traverse_method = self.traverse_many
                        path.append((source, target))
                        traverse_method(path[:], attr, source_attr_proxy,
                                        target_attr_proxy, visitor)
                        path.pop()
            visitor.visit_one(path, attribute, source, target)

    def traverse_many(self, path, attribute, source_sequence,
                      target_sequence, visitor):
        """
        :param source_sequence: iterable of source data proxies
        :type source_sequence: iterable yielding instances of
                               `DataTraversalProxy` or None
        :param target_sequence: iterable of target data proxies
        :type target_sequence: iterable yielding instances of
                               `DataTraversalProxy` or None
        """
        target_map = {}
        if not target_sequence is None:
            for target in target_sequence.get_value(attribute):
                target_map[target.get_id()] = target
        if not source_sequence is None:
            for source in source_sequence.get_value(attribute):
                source_id = source.get_id()
                if not source_id is None:
                    # All not-None IDs must have an existing target: UPDATE
                    try:
                        target = target_map.pop(source_id)
                    except KeyError:
                        raise ValueError('Trying to update non-existing '
                                         'target with ID %s for attribute '
                                         '%s.' % (source_id, attribute))
                else:
                    # Target does not exist: ADD
                    target = None
                self.traverse_one(path, attribute, source, target, visitor)
        # All targets that are now still in the map where not present in the
        # source and therefore need to be REMOVEd.
        for target in itervalues_(target_map):
            self.traverse_one(path, attribute, None, target, visitor)
        visitor.visit_many(path, attribute, source_sequence, target_sequence)


class DataTreeVisitor(object):
    def __init__(self, rc_class):
        self._rc_class = rc_class

    def visit_one(self, path, attribute, source, target):
        raise NotImplementedError('Abstract method.')

    def visit_many(self, path, attr, source, target):
        raise NotImplementedError('Abstract method.')


class AruVisitor(DataTreeVisitor):
    def __init__(self, rc_class, add_callback=None, remove_callback=None,
                 update_callback=None):
        DataTreeVisitor.__init__(self, rc_class)
        self.__add_callback = add_callback
        self.__remove_callback = remove_callback
        self.__update_callback = update_callback
        #: The root of the new source tree (ADD) or of the updated target
        #: tree (UPDATE) or None (REMOVE).
        self.root = None

    def visit_one(self, path, attribute, source, target):
        if attribute is None:
            # Visiting the root.
            ent_class = get_entity_class(self._rc_class)
        else:
            ent_class = get_entity_class(attribute.attr_type)
        if source is None:
            # No source - REMOVE.
            if not self.__remove_callback is None:
                self.__remove_callback(ent_class, target.as_domain_object())
        else:
            if target is None:
                entity = source.as_domain_object()
                # No target - ADD.
                if not self.__add_callback is None:
                    self.__add_callback(ent_class, entity)
                if len(path) > 0:
                    # When ADDing new entities, we have to update the
                    # parent's attribute with the newly created entity.
                    parent = path[-1][0]
                    parent.set_value(attribute, entity)
            else:
                entity = target.as_domain_object()
                # Both source and target - UPDATE.
                if not self.__update_callback is None:
                    self.__update_callback(ent_class,
                                           entity,
                                           source.as_attribute_value_map())
            if attribute is None:
                self.root = entity

    def visit_many(self, path, attr, source, target):
        pass


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
#    def __remove(self, entity_class, entity, relationship=None):
#        if not relationship is None:
#            # Visiting the root.
#            self.__remove_callback(entity_class, entity)
#        self.__remove_callback(entity_class, entity)
