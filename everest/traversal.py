"""
Custom resource object tree traverser.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 4, 2011.
"""
from collections import MutableSequence
from collections import MutableSet
from everest.attributes import get_attribute_cardinality
from everest.attributes import is_terminal_attribute
from everest.constants import CARDINALITY_CONSTANTS
from everest.constants import RELATION_OPERATIONS
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.constants import RESOURCE_KINDS
from everest.interfaces import IDataTraversalProxyAdapter
from everest.interfaces import IDataTraversalProxyFactory
from everest.resources.interfaces import IResource
from everest.traversalpath import TraversalPath
from logging import getLogger as get_logger
from pyramid.compat import itervalues_
from pyramid.threadlocal import get_current_registry
from pyramid.traversal import ResourceTreeTraverser
from zope.interface import implementer # pylint: disable=E0611,F0401
#from everest.resources.staging import create_staging_collection

__docformat__ = 'reStructuredText en'
__all__ = ['ConvertingDataTraversalProxyMixin',
           'DataSequenceTraversalProxy',
           'DataTraversalProxy',
           'DataTraversalProxyAdapter',
           'DataTraversalProxyFactory',
           'SourceTargetDataTreeTraverser',
           'SuffixResourceTraverser',
           ]


class SuffixResourceTraverser(ResourceTreeTraverser):
    """
    A custom resource tree traverser that allows us to specify the
    representation for resources with a suffix as in
    `http://everest/myobjects.csv`.

    Rather than to reproduce the functionality of the `__call__` method, we
    check if base part of the current view name (`myobjects` in the example)
    can be retrieved as a child resource from the context. If yes, we set the
    context to the resource and the view name to the extension part of the
    current view name (`csv` in the example); if no, nothing is changed.
    """
    def __call__(self, request):
        system = ResourceTreeTraverser.__call__(self, request)
        context = system['context']
        view_name = system['view_name']
        if IResource.providedBy(context) and '.' in view_name: # pylint: disable=E1101
            rc_name, repr_name = view_name.split('.')
            try:
                child_rc = context[rc_name]
            except KeyError:
                pass
            else:
                if IResource.providedBy(child_rc): # pylint: disable=E1101
                    system['context'] = child_rc
                    system['view_name'] = repr_name
        return system


class DataSequenceTraversalProxy(object):
    """
    Simple wrapper for a sequence of data traversal proxies.
    """
    #: Constant indicating that this proxy is for collection resource data.
    proxy_for = RESOURCE_KINDS.COLLECTION

    def __init__(self, proxies):
        self.__proxies = proxies

    def __iter__(self):
        return iter(self.__proxies)


class DataTraversalProxy(object):
    """
    Abstract base class for data tree traversal proxies.

    By providing a uniform interface to the nodes of data trees
    encountered during tree traversal, this proxy makes it possible to use
    different data structures as source or target for the traversal.
    """
    #: Constant indicating that this proxy is for member resource data.
    proxy_for = RESOURCE_KINDS.MEMBER

    def __init__(self, data, accessor, relationship_direction):
        """
        :param data: root of the data tree to traverse.
        :param relationship_direction: constant indicating which relation
          direction(s) to consider for managing references.
        """
        super(DataTraversalProxy, self).__init__()
        self.relationship_direction = relationship_direction
        self._data = data
        self._accessor = accessor
        self._relationships = {}

    def get_relationship_attributes(self):
        """
        Returns an iterator over the relationship attributes (i.e.,
        non-terminal attributes) of the proxied data.

        :returns: iterator yielding objects implementing
          :class:`everest.resources.interfaces.IResourceAttribute`.
        """
        for attr in self._attribute_iterator():
            if not is_terminal_attribute(attr):
                yield attr

    def get_matching(self, source_id):
        """
        Returns a matching target object for the given source ID.
        """
        value = self._accessor.get_by_id(source_id)
        if not value is None:
            reg = get_current_registry()
            prx_fac = reg.getUtility(IDataTraversalProxyFactory)
            prx = prx_fac.make_proxy(value,
                                     self._accessor,
                                     self.relationship_direction)
        else:
            prx = None
        return prx

    @property
    def update_attribute_value_items(self):
        """
        Returns an iterator of items for an attribute value map to use for
        an UPDATE operation.

        The iterator ignores collection attributes as these are processed
        implicitly by the traversal algorithm.

        :returns: iterator yielding tuples with objects implementing
          :class:`everest.resources.interfaces.IResourceAttribute` as the
          first and the proxied attribute value as the second argument.
        """
        for attr in self._attribute_iterator():
            if attr.kind != RESOURCE_ATTRIBUTE_KINDS.COLLECTION:
                try:
                    attr_val = self._get_proxied_attribute_value(attr)
                except AttributeError:
                    continue
                else:
                    yield (attr, attr_val)

    def set_relationship(self, attribute, relationship):
        """
        Sets the given domain relationship object for the given resource
        attribute.
        """
        self._relationships[attribute.entity_attr] = relationship

    def get_relationship(self, attribute):
        """
        Returns the domain relationship object for the given resource
        attribute.
        """
        return self._relationships[attribute.entity_attr]

    def get_attribute_proxy(self, attribute):
        """
        Returns a traversal proxy (cardinality ONE) or an iterable sequence
        data traversal proxy (cardinality MANY) for the specified relation
        attribute value of the proxied data.

        :raises ValueError: If :param:`attribute` is a terminal attribute.
        """
        attr_val = self._get_relation_attribute_value(attribute)
        if attr_val is None:
            prx = None
        else:
            if not self._accessor is None:
                acc = self._make_accessor(attribute.attr_type)
            else:
                acc = None
            reg = get_current_registry()
            prx_fac = reg.getUtility(IDataTraversalProxyFactory)
            prx = prx_fac.make_proxy(attr_val, acc,
                                     self.relationship_direction,
                                     options=
                                        self._get_proxy_options(attribute))
        return prx

    def do_traverse(self):
        """
        Checks if this proxy should be traversed.
        """
        return True

    def _get_proxy_options(self, attribute): # pylint:disable=W0613
        """
        Returns custom constructor options to pass to new proxies constructed
        from this one through :method:`get_attribute_proxy`. This default
        implementation returns an emtpy dictionary.
        """
        return {}

    def _get_relatee(self, attribute):
        """
        Returns the relatee for the given relation attribute.

        :raises AttributeError: If no relatee for the given attribute has
          been set.
        """
        try:
            rel = self._relationships[attribute.entity_attr]
        except KeyError:
            raise AttributeError(attribute)
        else:
            return rel.relatee

    def get_id(self):
        """
        Returns the ID of the proxied data.

        :returns: Numeric or string ID.
        """
        raise NotImplementedError('Abstract method.')

    def _get_entity_type(self):
        """
        Returns the entity type of the proxied data.

        :returns: Type object (subclass of
          :class:`everest.entities.base.Entity`)
        """
        raise NotImplementedError('Abstract method.')

    def get_entity(self):
        """
        Returns the proxied data as a domain object.

        :returns: Instance of :class:`everest.entities.base.Entity`.
        """
        raise NotImplementedError('Abstract method.')

    def _attribute_iterator(self):
        """
        Returns an iterator over all proxied resource attributes.
        """
        raise NotImplementedError('Abstract method.')

    def _get_relation_attribute_value(self, attribute):
        """
        Returns the value for the given relation attribute from the proxied
        data. Depending on the implementation, a sequence of data items may
        be returned for attributes of cardinality MANY.
        """
        raise NotImplementedError('Abstract method.')

    def _get_proxied_attribute_value(self, attribute):
        """
        Returns the value for the given attribute from the proxied data.

        :raises AttributeError: If the proxied data do not have the specified
          attribute.
        """
        raise NotImplementedError('Abstract method.')

    def _make_accessor(self, value_type):
        """
        Creates a new target accessor for the given value.
        """
        raise NotImplementedError('Abstract method.')

    def __str__(self):
        return "%s(id=%s)" % (self._data.__class__.__name__, self.get_id())

    def __hash__(self):
        """
        The hash value is built either from the ID and the entity type of
        the proxied data or, if the ID is None, from the runtime object
        ID.
        """
        data_id = self.get_id()
        return data_id is None and id(self._data) \
               or hash((self._get_entity_type(), data_id))

    def __eq__(self, other):
        """
        Equality is determined by comparing hash values.
        """
        return self.__hash__() == hash(other)


@implementer(IDataTraversalProxyFactory)
class DataTraversalProxyFactory(object):
    """
    Factory for data traversal proxies.
    """
    def make_source_proxy(self, data, options=None):
        """
        Returns a data traversal proxy for the given source data.

        This is a convenience factory function to use when manually setting
        up a data traversal proxy for source data.

        :raises ValueError: If there is no adapter for the given traversal
          data and the data is not iterable.
        """
        return self.__make_proxy('make_source_proxy', data, (),
                                 dict(options=options))

    def make_target_proxy(self, data, accessor, manage_back_references=True,
                          options=None):
        """
        Returns a data traversal proxy for the given target data.

        This is a convenience factory function to use when manually setting
        up a data traversal proxy for target data.

        :raises ValueError: If there is no adapter for the given traversal
          data and the data is not iterable.
        """
        return self.__make_proxy('make_target_proxy', data, (accessor,),
                                 dict(manage_back_references=
                                            manage_back_references,
                                      options=options))

    def make_proxy(self, data, accessor, relationship_direction,
                   options=None):
        """
        Returns a data traversal proxy for the given data.

        This is the generic factory function that can be used to create
        both source and target data traversal proxies.

        :raises ValueError: If there is no adapter for the given traversal
          data and the data is not iterable.
        """
        return self.__make_proxy('make_proxy', data,
                                 (accessor, relationship_direction),
                                 dict(options=options))

    def __make_proxy(self, method_name, data, args, options):
        # We first check if we have a registered adapter for the given data;
        # if not, we assume it is a mutable sequence or set; if that fails,
        # we raise a ValueError.
        reg = get_current_registry()
        adp = reg.queryAdapter(data, IDataTraversalProxyAdapter)
        if not adp is None:
            prx = getattr(adp, method_name)(*args, **options)
        else:
            if not isinstance(data, (MutableSequence, MutableSet)):
                # Assuming an iterable is not enough here.
                raise ValueError('Invalid data type for traversal: %s.'
                                 % type(data))
            else:
                prxs = []
                for item in data:
                    adp = reg.queryAdapter(item, IDataTraversalProxyAdapter)
                    if adp is None:
                        raise ValueError('Invalid data type for traversal: '
                                         '%s.' % type(item))
                    prx = getattr(adp, method_name)(*args, **options)
                    prxs.append(prx)
                prx = DataSequenceTraversalProxy(prxs)
        return prx


@implementer(IDataTraversalProxyAdapter)
class DataTraversalProxyAdapter(object):
    """
    Abstract base class for data traversal proxy adapters.

    The adapters are used for dispatching a new data traversal proxy based
    on a resource data tree node's value.
    """
    #: The data traversal proxy class used by this factory.
    proxy_class = lambda *args: None

    def __init__(self, data):
        self._data = data

    def make_source_proxy(self, options=None):
        """
        Returns a data traversal proxy for the adapted data.
        """
        raise NotImplementedError('Abstract method.')

    def make_target_proxy(self, accessor, manage_back_references=True,
                          options=None):
        """
        Returns a data traversal proxy for the adapted data.
        """
        raise NotImplementedError('Abstract method.')

    def make_proxy(self, accessor, relationship_direction, options=None):
        """
        Returns a data traversal proxy for the adapted data.
        """
        if options is None:
            options = {}
        return self.proxy_class(self._data, accessor,
                                   relationship_direction, **options)


class ConvertingDataTraversalProxyMixin(object):
    """
    Mixin class for data traversal proxies that convert incoming
    representation data to an entity.
    """
    __converted_entity = None

    def get_entity(self):
        """
        Returns the entity converted from the proxied data.
        """
        if self._accessor is None:
            if self.__converted_entity is None:
                self.__converted_entity = self._convert_to_entity()
        else:
            # If we have an accessor, we can get the proxied entity by ID.
            # FIXME: This is a hack that is only used for REMOVE operations
            #        with data elements.
            self.__converted_entity = \
                self.get_matching(self.get_id()).get_entity()
        return self.__converted_entity

    def _convert_to_entity(self):
        raise NotImplementedError('Abstract method.')


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
    being removed is also removed if it has an ID (i.e., the "id" attribute
    is not None).
    """
    def __init__(self, source_proxy, target_proxy):
        self._src_prx = source_proxy
        self._tgt_prx = target_proxy
        self.__traversed = set()
        self.__root_is_sequence = \
            (not source_proxy is None and
             source_proxy.proxy_for == RESOURCE_KINDS.COLLECTION) \
            or (not target_proxy is None and
                target_proxy.proxy_for == RESOURCE_KINDS.COLLECTION)
        if __debug__:
            self.__logger = get_logger('everest')
        else:
            self.__logger = None

    @classmethod
    def make_traverser(cls, source_data, target_data, relation_operation,
                       accessor=None, manage_back_references=True,
                       source_proxy_options=None, target_proxy_options=None):
        """
        Factory method to create a tree traverser depending on the input
        source and target data combination.

        :param source_data: Source data.
        :param target_target: Target data.
        :param str relation_operation: Relation operation. On of the constants
          defined in :class:`everest.constants.RELATION_OPERATIONS`.
        :param accessor: Accessor for looking up target nodes for update
          operations.
        :param bool manage_back_references: Flag passed to the target proxy.
        """
        reg = get_current_registry()
        prx_fac = reg.getUtility(IDataTraversalProxyFactory)
        if relation_operation == RELATION_OPERATIONS.ADD \
           or relation_operation == RELATION_OPERATIONS.UPDATE:
            if relation_operation == RELATION_OPERATIONS.ADD \
               and not target_data is None:
                raise ValueError('Must not provide target data with '
                                 'relation operation ADD.')
            source_proxy = \
                    prx_fac.make_source_proxy(source_data,
                                              options=source_proxy_options)
            source_is_sequence = \
                source_proxy.proxy_for == RESOURCE_KINDS.COLLECTION
            if not source_is_sequence:
                source_id = source_proxy.get_id()
        else:
            source_proxy = None
            source_is_sequence = False
        if relation_operation == RELATION_OPERATIONS.REMOVE \
           or relation_operation == RELATION_OPERATIONS.UPDATE:
            if target_proxy_options is None:
                target_proxy_options = {}
            if relation_operation == RELATION_OPERATIONS.REMOVE:
                if not source_data is None:
                    raise ValueError('Must not provide source data with '
                                     'relation operation REMOVE.')
                target_proxy = prx_fac.make_target_proxy(
                                            target_data,
                                            accessor,
                                            manage_back_references=
                                                     manage_back_references,
                                            options=target_proxy_options)
            else: # UPDATE
                if accessor is None:
                    raise ValueError('Need to provide an accessor when '
                                     'performing UPDATE operations.')
                if not target_data is None:
                    target_root = target_data
                elif not source_is_sequence:
                    # Look up the (single) target to update.
                    target_root = accessor.get_by_id(source_id)
                    if target_root is None:
                        raise ValueError('Entity with ID %s to update not '
                                         'found.' % source_id)
                else:
                    # Look up collection of targets to update.
                    target_root = []
                    for src_prx in source_proxy:
                        tgt_ent_id = src_prx.get_id()
                        if tgt_ent_id is None:
                            continue
                        tgt_ent = accessor.get_by_id(tgt_ent_id)
                        if tgt_ent is None:
                            continue
                        target_root.append(tgt_ent)
                target_proxy = prx_fac.make_target_proxy(
                                            target_root,
                                            accessor,
                                            manage_back_references=
                                                 manage_back_references,
                                            options=target_proxy_options)
            target_is_sequence = \
                    target_proxy.proxy_for == RESOURCE_KINDS.COLLECTION
        else:
            target_proxy = None
            target_is_sequence = False
        if not source_proxy is None and not target_proxy is None:
            # Check for source/target consistency.
            if not ((source_is_sequence and target_is_sequence) or
                    (not source_is_sequence and not target_is_sequence)):
                raise ValueError('When both source and target root nodes are '
                                 'given, they can either both be sequences '
                                 'or both not be sequences.')
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
        path = TraversalPath()
        if self.__root_is_sequence:
            if not self._tgt_prx is None:
                tgts = iter(self._tgt_prx)
            else:
                tgts = None
            if not self._src_prx is None:
                srcs = iter(self._src_prx)
            else:
                srcs = None
            self.traverse_many(path, None, srcs, tgts, visitor)
        else:
            self.traverse_one(path, None, self._src_prx, self._tgt_prx,
                              visitor)
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
        prx = source or target
        if prx.do_traverse():
            rel_op = RELATION_OPERATIONS.check(source, target)
            for attr in prx.get_relationship_attributes():
                # Check cascade settings.
                if not bool(attr.cascade & rel_op):
                    continue
                if not source is None:
                    attr_source = source.get_attribute_proxy(attr)
                else:
                    attr_source = None
                if not target is None:
                    attr_target = target.get_attribute_proxy(attr)
                else:
                    attr_target = None
                attr_rel_op = RELATION_OPERATIONS.check(attr_source,
                                                        attr_target)
                if attr_rel_op == RELATION_OPERATIONS.ADD:
                    if rel_op == RELATION_OPERATIONS.ADD:
                        parent = source
                    else:
                        parent = target
                elif attr_rel_op == RELATION_OPERATIONS.REMOVE:
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
                    key = (attr_source, attr_target)
                    if key in self.__traversed:
                        continue
                    if attr_rel_op == RELATION_OPERATIONS.ADD:
#                        if not attr_source.get_id() is None:
#                            # We only ADD new items.
#                            continue
                        src_items = [attr_source]
                        tgt_items = None
                    elif attr_rel_op == RELATION_OPERATIONS.REMOVE:
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
                path.push(parent, attr, rel_op)
                self.traverse_many(path.clone(), attr, src_items, tgt_items,
                                   visitor)
                path.pop()
        visitor.visit(path, attribute, source, target)

    def traverse_many(self, path, attribute, source_sequence,
                      target_sequence, visitor):
        """
        Traverses the given source and target sequences and makes appropriate
        calls to :method:`traverse_one`.

        Algorithm:
        1) Build a map target item ID -> target data item from the target
           sequence;
        2) For each source data item in the source sequence check if it
           has a not-None ID; if yes, remove the corresponding target from the
           map generated in step 1) and use as target data item for the
           source data item; if no, use `None` as target data item;
        3) For the remaining items in the target map from 1), call
           :method:`traverse_one` passing `None` as source (REMOVE);
        4) For all source/target data item pairs generated in 2, call
           :method:`traverse_one` (ADD or UPDATE depending on whether target
           item is `None`).

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
        if target is None:
            mode = 'ADD'
            data = '%s,None' % source
        elif source is None:
            mode = 'REMOVE'
            data = 'None,%s' % target
        else:
            mode = 'UPDATE'
            data = '%s,%s' % (source, target)
        if not attribute is None:
            parent = "(%s)" % path.parent
            self.__logger.debug('%s%s %s.%s (%s)' %
                                ("  "*len(path), mode, parent,
                                 attribute.resource_attr, data))
        else:
            self.__logger.debug('%s ROOT (%s)' % (mode, data))
