"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Aug 28, 2013.
"""
from collections import OrderedDict
from everest.attributes import AttributeValueMap
from everest.attributes import get_attribute_cardinality
from everest.attributes import is_terminal_attribute
from everest.constants import CARDINALITY_CONSTANTS
from everest.constants import RELATIONSHIP_DIRECTIONS
from everest.constants import RELATIONSHIP_OPERATIONS
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.constants import RESOURCE_KINDS
from everest.entities.attributes import get_domain_class_attribute_iterator
from everest.entities.interfaces import IEntity
from everest.entities.relationship import DomainRelationship
from everest.entities.utils import get_entity_class
from everest.representers.interfaces import ICollectionDataElement
from everest.representers.interfaces import ILinkedDataElement
from everest.representers.interfaces import IMemberDataElement
from everest.resources.attributes import get_resource_class_attribute_iterator
from everest.resources.interfaces import IMemberResource
from everest.resources.utils import get_resource_class_for_relation
from everest.resources.utils import url_to_resource
from everest.utils import get_nested_attribute
from everest.utils import set_nested_attribute
from logging import getLogger as get_logger
from pyramid.compat import iteritems_
from pyramid.compat import itervalues_
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['DataTraversalProxy',
           'SourceTargetDataTreeTraverser',
           ]


class LazyDomainRelationship(DomainRelationship):
    __relator_proxy = None
    __action = None
    __kw = None

    #: This is the relatee set dynamically through calls to .add and .update.
    relatee = None

    def _set_relator(self, relator):
        self.__relator_proxy = relator

    def _get_relator(self):
        return self.__relator_proxy.get_entity()

    relator = property(_get_relator, _set_relator)

    def add(self, related, direction=None, check_existing=False):
        self.__lazy_action(DomainRelationship.add, related,
                           dict(direction=direction,
                                check_existing=check_existing))

    def remove(self, related, direction=None, check_existing=False):
        self.__lazy_action(DomainRelationship.remove, related,
                           dict(direction=direction,
                                check_existing=check_existing))

    def update(self, related, direction=None):
        self.__lazy_action(DomainRelationship.update, related,
                           dict(direction=direction))

    def execute(self):
#        if self.descriptor.cardinality.relatee == CARDINALITY_CONSTANTS.ONE:
        self.__action(self, self.relatee, **self.__kw)
#        else:
#            for entity in self.relatee:
#                self.__action(self, entity)

    def __lazy_action(self, method, related, kw):
        self.__action = method
        self.relatee = related
        self.__kw = kw
#        if self.descriptor.cardinality.relatee == CARDINALITY_CONSTANTS.ONE:
#            self.relatee = related
#        else:
#            if self.relatee is None:
#                self.relatee = []
#            self.relatee.append(related)


class DataTraversalProxy(object):
    """
    Abstract base class for data tree traversal proxies.

    By providing a uniform interface to the nodes of data trees
    encountered during tree traversal, this proxy makes it possible to use
    different data structures as source or target for the traversal.
    """
    def __init__(self, data, relationship_direction):
        """
        :param data: root of the data tree to traverse.
        """
        super(DataTraversalProxy, self).__init__()
        self.relationship_direction = relationship_direction
        self._data = data
        self.__relationships = {}

    @property
    def attributes(self):
        return self._attribute_iterator()

    @property
    def relationship_attributes(self):
        for attr in self._attribute_iterator():
            if not is_terminal_attribute(attr):
                yield attr

    @property
    def attribute_value_items(self):
        for attr in self._attribute_iterator():
            yield (attr, self._get_proxied_attribute_value(attr))

    @property
    def update_attribute_value_items(self):
        for attr in self._attribute_iterator():
            if attr.kind != RESOURCE_ATTRIBUTE_KINDS.COLLECTION:
                try:
                    attr_val = self._get_proxied_attribute_value(attr)
                except AttributeError:
                    continue
                else:
                    yield (attr, attr_val)

    @classmethod
    def make_source_proxy(cls, data):
        """
        Returns a new traversal proxy instance for a source data node.

        :param data: source data node to traverse
        """
        if isinstance(data, AttributeValueMap):
            prx_cls = AttributeValueMapDataTraversalProxy
            args = (data,)
            rel_drct = RELATIONSHIP_DIRECTIONS.REVERSE
        else:
            ifcs = provided_by(data)
            if IEntity in ifcs:
                prx_cls = DomainDataTraversalProxy
                args = (data, None)
                rel_drct = RELATIONSHIP_DIRECTIONS.NONE
            elif IMemberResource in ifcs:
                prx_cls = ResourceDataTraversalProxy
                args = (data, None)
                rel_drct = RELATIONSHIP_DIRECTIONS.NONE
            elif IMemberDataElement in ifcs:
                prx_cls = DataElementDataTraversalProxy
                args = (data,)
                rel_drct = RELATIONSHIP_DIRECTIONS.REVERSE
            else:
                raise ValueError('Invalid data for source traversal proxy for '
                                 '"%s".' % data)
        args += (rel_drct,)
        return prx_cls(*args)

    @classmethod
    def make_target_proxy(cls, data, accessor, manage_back_references=True):
        """
        Returns a new traversal proxy instance for a target data node.

        :param data: target data node to traverse
        :param accessor: an accessor for retrieving other nodes of the same
          type as :param:`data` by ID.
        :param bool manage_back_references: specifies whether relationship
          operations should also update the back reference. Defaults to
          `True`.
        """
        ifcs = provided_by(data)
        if IEntity in ifcs:
            prx_cls = DomainDataTraversalProxy
        elif IMemberResource in ifcs:
            prx_cls = ResourceDataTraversalProxy
        else:
            raise ValueError('Invalid data for target traversal proxy for '
                             '"%s".' % data)
        args = (data, accessor)
        rel_drct = RELATIONSHIP_DIRECTIONS.BIDIRECTIONAL
        if not manage_back_references:
            rel_drct &= ~RELATIONSHIP_DIRECTIONS.REVERSE
        args += (rel_drct,)
        return prx_cls(*args)

    def make_relationship(self, attribute, direction):
        """
        Create lazy relationship for the given attribute using this proxy as
        relator.
        """
        rel = self.__relationships.get(attribute.entity_attr)
        if rel is None:
            rel = LazyDomainRelationship(self, attribute, direction=direction)
            self.__relationships[attribute.entity_attr] = rel
#        if rel.direction != direction:
#            raise ValueError('Can not change direction after a relationship'
#                             'for an attribute has been created.')
        return rel
#        return attribute.make_relationship(self.get_entity(),
#                                                        direction=direction)

    def get_proxy(self, attribute):
        """
        Returns a traversal proxy (cardinality ONE) or a sequence of traversal
        proxies (cardinality MANY) for the specified relationship attribute
        value of the proxied data.

        :raises ValueError: If :param:`attribute` is a terminal attribute.
        """
        attr_val = self._get_attribute_value(attribute)
        if attr_val is None:
            val = None
        else:
            if get_attribute_cardinality(attribute) \
               == CARDINALITY_CONSTANTS.ONE:
                val = self._make_proxy_for_value(attr_val)
            else:
                val = (self._make_proxy_for_value(item) for item in attr_val)
        return val

    def _make_proxy_for_value(self, data):
        """
        Instantiates a new proxy for the given data.
        """
        return self.__class__(data, self.relationship_direction)

    def get_id(self):
        """
        Returns the ID of the proxied data.
        """
        raise NotImplementedError('Abstract method.')

    def do_traverse(self, attribute):
        """
        Checks if the given attribute of the proxied data should be traversed.
        """
        raise NotImplementedError('Abstract method.')

    def get_type(self):
        """
        Returns the type of the proxied data.
        """
        raise NotImplementedError('Abstract method.')

    def get_entity(self):
        """
        Returns the proxied data as a domain object.
        """
        raise NotImplementedError('Abstract method.')

    def _attribute_iterator(self):
        """
        Returns a dictionary mapping attribute names to attributes.
        """
        raise NotImplementedError('Abstract method.')

    def _get_attribute_value(self, attribute):
        """
        Returns the value for the given attribute from the proxied data.
        """
        raise NotImplementedError('Abstract method.')

    def _get_proxied_attribute_value(self, attribute):
        """
        Returns the value for the given attribute from the proxied data.
        """
        raise NotImplementedError('Abstract method.')

    def __str__(self):
        return "%s(id=%s)" % (self._data.__class__.__name__, self.get_id())

    def __hash__(self):
        """
        Returns ID of the proxied data.
        """
        return id(self._data)

    def __eq__(self, other):
        """
        Checks if the given other value is an instance of this class and
        if the other value's proxied data have the same ID.
        """
        return isinstance(other, self.__class__) \
               and id(self._data) == id(other._data) # pylint: disable=W0212


class AccessorDataTraversalProxyMixin(object):
    def __init__(self, data, accessor, relationship_direction):
        constr = super(AccessorDataTraversalProxyMixin, self).__init__
        constr(data, relationship_direction)
        self._accessor = accessor

    def get_matching(self, source_id):
        return self._accessor.get_by_id(source_id)

    def _make_proxy_for_value(self, value):
        if self._accessor is None:
            acc = None
        else:
            acc = self._accessor.get_root_aggregate(value)
        return self.__class__(value, acc, self.relationship_direction)


class DomainDataTraversalProxy(AccessorDataTraversalProxyMixin,
                               DataTraversalProxy):
    def get_id(self):
        return self._data.id

    def do_traverse(self, attribute):
        return True

    def get_type(self):
        return type(self._data)

    def get_entity(self):
        return self._data

    def _attribute_iterator(self):
        it = get_domain_class_attribute_iterator(self._data)
        for attr in it:
            if not attr.entity_attr is None:
                yield attr

    def _get_attribute_value(self, attribute):
        return get_nested_attribute(self._data, attribute.entity_attr)

    def _get_proxied_attribute_value(self, attribute):
        return get_nested_attribute(self._data, attribute.entity_attr)


class ResourceDataTraversalProxy(AccessorDataTraversalProxyMixin,
                                 DataTraversalProxy):
    def get_id(self):
        return self._data.id

    def do_traverse(self, attribute):
        return True

    def get_type(self):
        return type(self._data)

    def get_entity(self):
        return self._data.get_entity()

    def _attribute_iterator(self):
        return get_resource_class_attribute_iterator(self._data)

    def _get_attribute_value(self, attribute):
        return get_nested_attribute(self._data, attribute.resource_attr)

    def _get_proxied_attribute_value(self, attribute):
        return get_nested_attribute(self._data, attribute.resource_attr)


class ConvertingDataTraversalProxyMixin(object):
    def __init__(self, data, relationship_direction):
        constr = super(ConvertingDataTraversalProxyMixin, self).__init__
        constr(data, relationship_direction)
        self.__relationship_data = {}
        self.__converted_entity = None

    def make_relationship(self, attribute, direction):
        try:
            rel = self.__relationship_data[attribute.entity_attr]
        except KeyError:
            rel = LazyDomainRelationship(self, attribute,
                                         direction=direction)
            self.__relationship_data[attribute.entity_attr] = rel
        return rel

    def get_entity(self):
        if self.__converted_entity is None:
            self.__converted_entity = self._convert_to_entity()
            if self.relationship_direction \
               & RELATIONSHIP_DIRECTIONS.REVERSE:
                # Now that the relator (converted entity) exists, we can
                # execute the lazy relationship operations.
                for rel in itervalues_(self.__relationship_data):
                    rel.execute()
        return self.__converted_entity

    def _convert_link(self, link_data_el):
        url = link_data_el.get_url()
        rc = url_to_resource(url)
        return rc.get_entity()

    def _get_relatee(self, name):
        rel = self.__relationship_data[name]
        return rel.relatee

    def _convert_to_entity(self):
        raise NotImplementedError('Abstract method.')


class DataElementDataTraversalProxy(ConvertingDataTraversalProxyMixin,
                                    DataTraversalProxy):
    def get_id(self):
        if not ILinkedDataElement.providedBy(self._data): # pylint:disable=E1101
            id_attr = self._data.mapping.get_attribute_map()['id']
            id_val = self._data.get_terminal(id_attr)
        else:
            id_val = self._data.get_url().rstrip('/').split('/')[-1]
        return id_val

    def do_traverse(self, attribute):
        value = self._data.get_nested(attribute)
        is_link = ILinkedDataElement.providedBy(value) # pylint:disable=E1101
        return not (is_link and value.get_kind() == RESOURCE_KINDS.MEMBER)

    def get_type(self):
        if ILinkedDataElement.providedBy(self._data): # pylint:disable=E1101
            rel = self._data.get_relation()
            data_type = get_resource_class_for_relation(rel)
        else:
            data_type = self._data.mapping.mapped_class
        return data_type

    def _attribute_iterator(self):
        return self._data.mapping.attribute_iterator(
                                            mapped_class=self.get_type())

    def _get_attribute_value(self, attribute):
        data_el = self._data.get_nested(attribute)
        if ICollectionDataElement.providedBy(data_el): # pylint: disable=E1101
            attr_val = (mb_el for mb_el in data_el.get_members())
        else:
            attr_val = data_el
        return attr_val

    def _get_proxied_attribute_value(self, attribute):
        if is_terminal_attribute(attribute):
            # Terminal values are fetched from the data element.
            val = self._data.get_terminal(attribute)
        else:
            try:
                val = self._get_relatee(attribute.entity_attr)
            except KeyError:
                attr_data_el = self._data.get_nested(attribute)
                if attr_data_el is None:
                    val = None
                else:
                    ifcs = provided_by(attr_data_el)
                    if ILinkedDataElement in ifcs:
                        val = self._convert_link(attr_data_el)
                    elif ICollectionDataElement in ifcs \
                         and len(attr_data_el.get_members()) == 0:
                        # Empty source collections are not traversed.
                        val = []
                    else:
                        raise AttributeError(attribute)
        return val

    def _convert_to_entity(self):
        data_el = self._data
        init_map = {}
        nested_map = {}
        for attr in data_el.mapping.attribute_iterator():
            val = self._get_proxied_attribute_value(attr)
            attr_name = attr.entity_attr
            if not '.' in attr_name:
                init_map[attr_name] = val
            else:
                nested_map[attr_name] = val
        ent_cls = get_entity_class(data_el.mapping.mapped_class)
        entity = ent_cls.create_from_data(init_map)
        for nested_name, nested_value in iteritems_(nested_map):
            set_nested_attribute(entity, nested_name, nested_value)
        return entity

    def __str__(self):
        if ILinkedDataElement.providedBy(self._data): # pylint: disable=E1101
            _str = "Link(url=%s)" % self._data.get_url()
        else:
            _str = "%s(id=%s)" % (self._data.__class__.__name__,
                                    self.get_id())
        return _str


class AttributeValueMapDataTraversalProxy(ConvertingDataTraversalProxyMixin,
                                          DataTraversalProxy):
    def get_id(self):
        return self._data['id']

    def do_traverse(self, attribute):
        return True

    def get_type(self):
        raise NotImplementedError('Not implemented.')
#        mb_cls = get_resource_class_for_relation(self._data['__class__'])
#        return get_entity_class(mb_cls)

    def _attribute_iterator(self):
        raise NotImplementedError('Not implemented.')
#        mb_cls = get_resource_class_for_relation(self._data['__class__'])
#        return get_resource_class_attribute_iterator(mb_cls)

    def get_update_data_map(self):
        return OrderedDict(
                    [(attr, value)
                     for (attr, value) in iteritems_(self._data)
                     if not attr.kind == RESOURCE_ATTRIBUTE_KINDS.COLLECTION])

    def __str__(self):
        return "->map(id=%s)" % self._data['id']

    def _get_attribute_value(self, attribute):
        return self._data.get(attribute)

    def _get_proxied_attribute_value(self, attribute):
        try:
            val = self._get_relatee(attribute.entity_attr)
        except KeyError:
            val = self._data.get(attribute)
        return val

    def _convert_to_entity(self):
        init_map = {}
        nested_map = {}
        for attr in self._data:
#            if attr == '__class__':
#                continue
            attr_name = attr.entity_attr
            val = self._get_proxied_attribute_value(attr)
            if not '.' in attr_name:
                init_map[attr_name] = val
            else:
                nested_map[attr_name] = val
        entity = self.get_type().create_from_data(init_map)
        for nested_name, nested_value in iteritems_(nested_map):
            set_nested_attribute(entity, nested_name, nested_value)
        return entity


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
    is suppressed when the parent attribute does not have the appropriate
    cascading flag set.

    When traversing along the ADD cascade, a child node of a node that is
    being added is only traversed (along the ADD cascade) when it has no ID
    (i.e., ID is None).

    When traversing along the REMOVE cascade, a child node of a node that is
    being removed when it has an ID (i.e., ID is not None).

    When traversing along the UPDATE cascade,
    """
    def __init__(self, source_proxy, target_proxy):
        if not source_proxy is None and not target_proxy is None \
           and source_proxy.get_id() != target_proxy.get_id():
            raise ValueError('When both source and target root nodes are '
                             'given, they both need to have the same ID.')
        self._src_prx = source_proxy
        self._tgt_prx = target_proxy
        self.__traversed = set()
        if __debug__:
            self.__logger = get_logger('everest')
        else:
            self.__logger = None

    @classmethod
    def make_traverser(cls, source_root, target_root, accessor,
                       manage_back_references=True):
#        if isinstance(source_root, AttributeValueMap) and target_root is None:
#            raise ValueError('Must supply a target root when traversing '
#                             'with an attribute value map.')
        if not source_root is None:
            source_proxy = DataTraversalProxy.make_source_proxy(source_root)
        else:
            source_proxy = None
        if not target_root is None:
            target_proxy = \
                DataTraversalProxy.make_target_proxy(target_root,
                                                     accessor,
                                                     manage_back_references=
                                                       manage_back_references)
        else:
            target_proxy = None
        return cls(source_proxy, target_proxy)

    def run(self, visitor):
        """
        :param visitor: visitor to call with every node in the domain tree.
        :type visitor: subclass of
            :class:`everest.entities.traversal.DomainVisitor`
        """
        if __debug__:
            self.__log_run(visitor)
        visitor.prepare()
        self.traverse_one([], None, self._src_prx, self._tgt_prx, visitor)
        visitor.finalize()

    def traverse_one(self, path, attribute, source, target, visitor):
        """
        :param source: source data proxy
        :type source: instance of `DataTraversalProxy` or None
        :param target: target data proxy
        :type target: instance of `DataTraversalProxy` or None
        """
        if __debug__:
            self.__log_traverse_one(path, attribute, source, target)
        self.__traversed.add((source, target))
#            # Look up the target for UPDATE.
#            target = self._tgt_prx.get_matching(attribute, source)
#            if target is None:
#                raise ValueError('If the source has an ID, a target with'
#                                 ' the same ID must exist.')
        prx = source or target
        rel_op = RELATIONSHIP_OPERATIONS.check(source, target)
        for attr in prx.relationship_attributes:
            # Check cascade settings.
            do_traverse = bool(attr.cascade & rel_op) \
                          & prx.do_traverse(attr)
            if do_traverse:
                if not source is None:
                    attr_source = source.get_proxy(attr)
                else:
                    attr_source = None
                if not target is None:
                    attr_target = target.get_proxy(attr)
                else:
                    attr_target = None
                attr_rel_op = RELATIONSHIP_OPERATIONS.check(attr_source,
                                                            attr_target)
                if attr_rel_op == RELATIONSHIP_OPERATIONS.ADD:
                    if rel_op == RELATIONSHIP_OPERATIONS.ADD:
                        parent = source
                    else:
                        parent = target
                elif attr_rel_op == RELATIONSHIP_OPERATIONS.REMOVE:
                    parent = target
                else: # UPDATE
                    parent = target
                card = get_attribute_cardinality(attr)
                if card == CARDINALITY_CONSTANTS.ONE:
                    if attr_source is None and attr_target is None:
                        # If both source and target have None values, there is
                        # nothing to do.
                        continue
                    # Check if we have already traversed this combination of
                    # source and target (circular references).
                    key = (attr_target, attr_target)
                    if key in self.__traversed:
                        continue
                    if attr_rel_op == RELATIONSHIP_OPERATIONS.ADD:
#                        if not attr_source.get_id() is None:
#                            # We only ADD new items.
#                            continue
                        src_items = [attr_source]
                        tgt_items = None
                    elif attr_rel_op == RELATIONSHIP_OPERATIONS.REMOVE:
                        src_items = None
                        tgt_items = [attr_target]
                    else: # UPDATE
                        src_items = [attr_source]
                        tgt_items = [attr_target]
                        src_id = attr_source.get_id()
                        tgt_id = attr_target.get_id()
                        if src_id != tgt_id:
                            src_target = attr_target.get_matching(src_id)
                            if not src_target is None:
                                tgt_items.append(src_target)
                else:
                    src_items = attr_source
                    tgt_items = attr_target
                path.append(parent)
                self.traverse_many(path[:], attr, src_items, tgt_items,
                                   visitor)
                path.pop()
        visitor.visit(path, attribute, source, target)

    def traverse_many(self, path, attribute, source_sequence,
                      target_sequence, visitor):
        """
        :param source_sequence: iterable of source data proxies
        :type source_sequence: iterator yielding instances of
                               `DataTraversalProxy` or None
        :param target_sequence: iterable of target data proxies
        :type target_sequence: iterator yielding instances of
                               `DataTraversalProxy` or None
        """
        target_map = {}
        if not target_sequence is None:
            for target in target_sequence:
                target_map[target.get_id()] = target
        src_tgt_pairs = []
        if not source_sequence is None:
            for source in source_sequence:
                source_id = source.get_id()
                if not source_id is None:
                    # Check if target exists for UPDATE.
                    target = target_map.pop(source_id, None)
                else:
                    # Source is new, there is no target, so ADD.
                    target = None
                src_tgt_pairs.append((source, target))
        # All targets that are now still in the map where not present in the
        # source and therefore need to be REMOVEd.
        for target in itervalues_(target_map):
            if not (None, target) in self.__traversed:
                self.traverse_one(path, attribute, None, target, visitor)
        #
        for source, target in src_tgt_pairs:
            if not (source, target) in self.__traversed:
                self.traverse_one(path, attribute, source, target, visitor)

    def __log_run(self, visitor):
        self.__logger.debug('Traversing %s->%s with %s'
                            % (self._src_prx, self._tgt_prx, visitor))

    def __log_traverse_one(self, path, attribute, source, target):
        if not attribute is None:
            parent = "(%s)" % path[-1]
            if target is None:
                mode = 'ADD'
                data = '%s,None' % source
            elif source is None:
                mode = 'REMOVE'
                data = 'None,%s' % target
            else:
                mode = 'UPDATE'
                data = '%s,%s' % (source, target)
            self.__logger.debug('%s%s %s.%s (%s)' %
                                ("  "*len(path), mode, parent,
                                 attribute.resource_attr, data))
