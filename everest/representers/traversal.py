"""
Resource data tree traversal.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 25, 2012.
"""
from collections import OrderedDict
from everest.attributes import is_terminal_attribute
from everest.constants import RELATIONSHIP_DIRECTIONS
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.constants import RESOURCE_KINDS
from everest.entities.utils import get_entity_class
from everest.interfaces import IDataTraversalProxyFactory
from everest.representers.attributes import MappedAttributeKey
from everest.representers.config import IGNORE_OPTION
from everest.representers.config import WRITE_AS_LINK_OPTION
from everest.representers.config import WRITE_MEMBERS_AS_LINK_OPTION
from everest.representers.interfaces import ICollectionDataElement
from everest.representers.interfaces import ILinkedDataElement
from everest.representers.interfaces import IMemberDataElement
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_member_class
from everest.traversal import ConvertingDataTraversalProxyMixin
from everest.traversal import DataTraversalProxy
from everest.traversal import DataTraversalProxyAdapter
from everest.utils import set_nested_attribute
from pyramid.compat import iteritems_
from pyramid.threadlocal import get_current_registry
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['DataElementBuilderRepresentationDataVisitor',
           'DataElementBuilderResourceDataVisitorBase',
           'DataElementBuilderResourceTreeVisitor',
           'DataElementDataTraversalProxy',
           'DataElementDataTraversalProxyAdapter',
           'DataElementTreeTraverser',
           'DataTreeTraverser',
           'DataElementTreeTraverser',
           'ResourceDataTreeTraverser',
           'ResourceDataVisitor',
           'ResourceTreeTraverser',
           ]


class ResourceDataVisitor(object):
    def visit_member(self, attribute_key, attribute, member_node, member_data,
                     is_link_node, parent_data, index=None):
        """
        Visits a member node in a resource data tree.

        :param tuple attribute_key: tuple containing the attribute tokens
          identifying the member node's position in the resource data tree.
        :param attribute: mapped attribute holding information about the
          member node's name (in the parent) and type etc.
        :type attribute:
          :class:`everest.representers.attributes.MappedAttribute`
        :param member_node: the node holding resource data. This is either a
          resource instance (when using a :class:`ResourceTreeTraverser` on
          a tree of resources) or a data element instance (when using a
          :class:`DataElementTreeTraverser` on a data element tree.
        :param dict member_data: dictionary holding all member data
          extracted during traversal (with mapped attributes as keys).
        :param bool is_link_node: indicates if the given member node is a link.
        :param dict parent_data: dictionary holding all parent data extracted
          during traversal (with mapped attributes as keys).
        :param int index: this indicates a member node's index in a collection
          parent node. If the parent node is a member node, it will be `None`.
        """
        raise NotImplementedError('Abstract method.')

    def visit_collection(self, attribute_key, attribute, collection_node,
                         collection_data, is_link_node, parent_data):
        """
        Visits a collection node in a resource data tree.

        :param tuple attribute_key: tuple containing the attribute tokens
          identifying the collection node's position in the resource data
          tree.
        :param attribute: mapped attribute holding information about the
          collection node's name (in the parent) and type etc.
        :type attribute:
          :class:`everest.representers.attributes.MappedAttribute`
        :param collection_node: the node holding resource data. This is either
          a resource instance (when using a :class:`ResourceTreeTraverser` on
          a tree of resources) or a data element instance (when using a
          :class:`DataElementTreeTraverser` on a data element tree.
        :param dict collection_data: dictionary mapping member index to member
          data for each member in the visited collection.
        :param bool is_link_node: indicates if the given member node is a link.
        :param dict parent_data: dictionary holding all parent data extracted
          during traversal (with mapped attributes as keys).
        """
        raise NotImplementedError('Abstract method.')


class DataElementBuilderResourceDataVisitorBase(ResourceDataVisitor):
    """
    Abstract base class for visitors creating a data element from resource
    data.
    """
    def __init__(self, mapping):
        ResourceDataVisitor.__init__(self)
        self._mapping = mapping
        self.__data_el = None

    def visit_member(self, attribute_key, attribute, member_node, member_data,
                     is_link_node, parent_data, index=None):
        if is_link_node:
            mb_data_el = self._create_link_data_element(attribute,
                                                        member_node)
        else:
            mb_data_el = self._create_member_data_element(attribute,
                                                          member_node)
            # Process attributes.
            for attr, value in iteritems_(member_data):
                if attr.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                    self._set_terminal_attribute(mb_data_el, attr, value)
                else:
                    mb_data_el.set_nested(attr, value)
        if not index is None:
            # Collection member. Store in parent data with index as key.
            parent_data[index] = mb_data_el
        elif len(attribute_key) == 0:
            # Top level - store root data element.
            self.__data_el = mb_data_el
        else:
            # Nested member. Store in parent data with attribute as key.
            parent_data[attribute] = mb_data_el

    def visit_collection(self, attribute_key, attribute, collection_node,
                         collection_data, is_link_node, parent_data):
        if is_link_node:
            coll_data_el = self._create_link_data_element(attribute,
                                                          collection_node)
        else:
            coll_data_el = \
                self._create_collection_data_element(attribute,
                                                     collection_node)
            for item in sorted(collection_data.items()):
                coll_data_el.add_member(item[1])
        if len(attribute_key) == 0: # Top level.
            self.__data_el = coll_data_el
        else:
            parent_data[attribute] = coll_data_el

    @property
    def data_element(self):
        return self.__data_el

    def _create_member_data_element(self, attribute, member_node):
        raise NotImplementedError('Abstract method.')

    def _create_collection_data_element(self, attribute, collection_node):
        raise NotImplementedError('Abstract method.')

    def _create_link_data_element(self, attribute, member_node):
        raise NotImplementedError('Abstract method.')

    def _set_terminal_attribute(self, data_element, attribute, value):
        raise NotImplementedError('Abstract method.')


class DataElementBuilderRepresentationDataVisitor(
                                    DataElementBuilderResourceDataVisitorBase):
    def _create_member_data_element(self, attribute, member_node):
        if not attribute is None:
            mb_cls = get_member_class(attribute.value_type)
        else:
            mb_cls = get_member_class(self._mapping.mapped_class)
        return self._mapping.create_data_element(mapped_class=mb_cls)

    def _create_collection_data_element(self, attribute, collection_node):
        if not attribute is None:
            coll_cls = get_collection_class(attribute.value_type)
        else:
            coll_cls = get_collection_class(self._mapping.mapped_class)
        return self._mapping.create_data_element(mapped_class=coll_cls)

    def _create_link_data_element(self, attribute, member_node):
        if attribute.kind == RESOURCE_ATTRIBUTE_KINDS.MEMBER:
            kind = RESOURCE_KINDS.MEMBER
            rc_cls = get_member_class(attribute.value_type)
        else:
            kind = RESOURCE_KINDS.COLLECTION
            rc_cls = get_collection_class(attribute.value_type)
        return self._mapping.create_linked_data_element(
                                                member_node, kind,
                                                relation=rc_cls.relation,
                                                title=rc_cls.title)

    def _set_terminal_attribute(self, data_element, attribute, value):
        data_element.set_terminal_converted(attribute, value)


class DataElementBuilderResourceTreeVisitor(
                                    DataElementBuilderResourceDataVisitorBase):
    def _create_member_data_element(self, attribute, member_node):
        return self._mapping.create_data_element_from_resource(member_node)

    def _create_collection_data_element(self, attribute, collection_node):
        return \
            self._mapping.create_data_element_from_resource(collection_node)

    def _create_link_data_element(self, attribute, member_node):
        return \
          self._mapping.create_linked_data_element_from_resource(member_node)

    def _set_terminal_attribute(self, data_element, attribute, value):
        data_element.set_terminal(attribute, value)


class DataTreeTraverser(object):
    """
    Abstract base class for data tree traversers.
    """
    def __init__(self, root):
        self.__root = root

    def run(self, visitor):
        """
        Runs this traverser.
        """
        self._dispatch(MappedAttributeKey(()), None, self.__root, None,
                       visitor)

    def _traverse_collection(self, attr_key, attr, collection_node,
                             parent_data, visitor):
        collection_data = {}
        is_link_node = \
            self._is_link_node(collection_node, attr) \
            and not (not attr is None and
                     attr.options.get(WRITE_MEMBERS_AS_LINK_OPTION) is True)
        if not is_link_node:
            all_mb_nodes = self._get_node_members(collection_node)
            for idx, mb_node in enumerate(all_mb_nodes):
                self._traverse_member(attr_key, attr, mb_node, collection_data,
                                      visitor, index=idx)
        visitor.visit_collection(attr_key, attr, collection_node,
                                 collection_data, is_link_node, parent_data)

    def _traverse_member(self, attr_key, attr, member_node, parent_data,
                         visitor, index=None):
        raise NotImplementedError('Abstract method.')

    def _is_link_node(self, node, attr):
        raise NotImplementedError('Abstract method.')

    def _get_node_members(self, node):
        raise NotImplementedError('Abstract method.')

    def _dispatch(self, attr_key, attr, node, parent_data, visitor):
        raise NotImplementedError('Abstract method.')


class ResourceDataTreeTraverser(DataTreeTraverser):
    """
    Abstract base class for resource data tree traversers.
    """
    def __init__(self, root, mapping, ignore_none_values=True):
        DataTreeTraverser.__init__(self, root)
        self._mapping = mapping
        self.__ignore_none_values = ignore_none_values

    def _traverse_member(self, attr_key, attr, member_node, parent_data,
                         visitor, index=None):
        member_data = OrderedDict()
        is_link_node = \
            self._is_link_node(member_node, attr) \
            or (not index is None and not attr is None and
                attr.options.get(WRITE_MEMBERS_AS_LINK_OPTION) is True)
        # Ignore links for traversal.
        if not is_link_node:
            if not attr is None:
                node_type = get_member_class(attr.value_type)
            else:
                node_type = self._get_node_type(member_node)
            for mb_attr in self._mapping.attribute_iterator(node_type,
                                                            attr_key):
                ignore_opt = self._get_ignore_option(mb_attr)
                if mb_attr.should_ignore(attr_key):
                    continue
                if mb_attr.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                    # Terminal attribute - extract.
                    value = self._get_node_terminal(member_node, mb_attr)
                    if value is None and self.__ignore_none_values:
                        # We ignore None attribute values when reading
                        # representations.
                        continue
                    member_data[mb_attr] = value
                else:
                    # Nested attribute - traverse.
                    nested_node = self._get_node_nested(member_node,
                                                        mb_attr)
                    if nested_node is None:
                        # Stop condition - the given data element does not
                        # contain a nested attribute of the given mapped
                        # name.
                        continue
                    nested_attr_key = attr_key + (mb_attr,)
                    if ignore_opt is False:
                        # The offset in the attribute key ensures that
                        # the defaults for ignoring attributes of the
                        # nested attribute can be retrieved correctly.
                        nested_attr_key.offset = len(nested_attr_key)
                    self._dispatch(nested_attr_key, mb_attr, nested_node,
                                   member_data, visitor)
        visitor.visit_member(attr_key, attr, member_node, member_data,
                             is_link_node, parent_data, index=index)

    def _get_node_type(self, node):
        raise NotImplementedError('Abstract method.')

    def _get_node_terminal(self, node, attr):
        raise NotImplementedError('Abstract method.')

    def _get_node_nested(self, node, attr):
        raise NotImplementedError('Abstract method.')

    def _get_ignore_option(self, attr):
        return attr.options.get(IGNORE_OPTION)


class DataElementTreeTraverser(ResourceDataTreeTraverser):
    """
    Traverser for data element trees.

    This legacy traverser is only needed to generate a representation from
    a data element tree.
    """
    def __init__(self, root, mapping,
                 ignore_none_values=True):
        ResourceDataTreeTraverser.__init__(
                                    self, root, mapping,
                                    ignore_none_values=ignore_none_values)

    def _dispatch(self, attr_key, attr, node, parent_data, visitor):
        ifcs = provided_by(node)
        if IMemberDataElement in ifcs:
            traverse_fn = self._traverse_member
        elif ICollectionDataElement in ifcs:
            traverse_fn = self._traverse_collection
        elif ILinkedDataElement in ifcs:
            kind = node.get_kind()
            if kind == RESOURCE_KINDS.MEMBER:
                traverse_fn = self._traverse_member
            else: # kind == RESOURCE_KINDS.COLLECTION
                traverse_fn = self._traverse_collection
        else:
            raise ValueError('Need MEMBER or COLLECTION data element; found '
                             '"%s".' % node)
        traverse_fn(attr_key, attr, node, parent_data, visitor)

    def _is_link_node(self, node, attr): # pylint: disable=W0613
        return ILinkedDataElement in provided_by(node)

    def _get_node_members(self, node):
        return node.get_members()

    def _get_node_type(self, node):
        return node.mapping.mapped_class

    def _get_node_terminal(self, node, attr):
        return node.get_terminal_converted(attr)

    def _get_node_nested(self, node, attr):
        return node.get_nested(attr)


class ResourceTreeTraverser(ResourceDataTreeTraverser):
    """
    Mapping traverser for resource trees.
    """
    def __init__(self, root, mapping, ignore_none_values=True):
        ResourceDataTreeTraverser.__init__(
                                    self, root, mapping,
                                    ignore_none_values=ignore_none_values)

    def _dispatch(self, attr_key, attr, node, parent_data, visitor):
        ifcs = provided_by(node)
        if IMemberResource in ifcs:
            self._traverse_member(attr_key, attr, node, parent_data, visitor)
        elif ICollectionResource in ifcs:
            self._traverse_collection(attr_key, attr, node, parent_data,
                                      visitor)
        else:
            raise ValueError('Can only traverse objects that provide'
                             'IMemberResource or ICollectionResource '
                             '(key: %s).' % str(attr_key))

    def _get_node_type(self, node):
        return type(node)

    def _get_node_terminal(self, node, attr):
        return getattr(node, attr.name)

    def _get_node_nested(self, node, attr):
        return getattr(node, attr.name)

    def _get_node_members(self, node):
        return iter(node)

    def _is_link_node(self, node, attr):
        return not attr is None and \
               not attr.options.get(WRITE_AS_LINK_OPTION) is False


class DataElementDataTraversalProxy(ConvertingDataTraversalProxyMixin,
                                    DataTraversalProxy):
    def __init__(self, data, accessor, relationship_direction,
                 attribute_key=None, mapping=None):
        """
        :param mapping: resource attribute mapping. This needs to be passed
          along to all other, nested proxies generated by this one in the
          traversal process.
        :type mapping: :class:`everest.representers.mapping.Mapping`
        """
        DataTraversalProxy.__init__(self, data, accessor,
                                    relationship_direction)
        if attribute_key is None:
            attribute_key = MappedAttributeKey(())
        self.__attribute_key = attribute_key
        if mapping is None:
            mapping = data.mapping
        self.__mapping = mapping

    def get_id(self):
        id_attr = self.__mapping.get_attribute_map()['id']
        return self._data.get_terminal(id_attr)

    def _get_entity_type(self):
        return get_entity_class(self._data.mapping.mapped_class)

    def _get_proxy_options(self, attribute):
        return dict(attribute_key=self.__attribute_key + (attribute,),
                    mapping=self.__mapping)

    def _attribute_iterator(self):
        return self.__mapping.attribute_iterator(
                                mapped_class=self._data.mapping.mapped_class,
                                key=self.__attribute_key)

    def _get_relation_attribute_value(self, attribute):
        # We use the access by representation name here which triggers an
        # AttributeError if the attribute was not set.
        return self._data.get_attribute(attribute.repr_name)

    def _get_proxied_attribute_value(self, attribute):
        if not is_terminal_attribute(attribute):
            val = self._get_relatee(attribute)
        else:
            val = self._data.get_attribute(attribute.repr_name)
        return val

    def _make_accessor(self, value_type):
        raise NotImplementedError('Not available for data element proxies.')

    def _convert_to_entity(self):
        init_map = {}
        nested_map = {}
        mapped_class = self._data.mapping.mapped_class
        for attr in \
            self.__mapping.attribute_iterator(mapped_class=mapped_class,
                                              key=self.__attribute_key):
            try:
                val = self._get_proxied_attribute_value(attr)
            except AttributeError:
                continue
            else:
                attr_name = attr.entity_attr
                if not '.' in attr_name:
                    init_map[attr_name] = val
                else:
                    nested_map[attr_name] = val
        ent_cls = get_entity_class(mapped_class)
        entity = ent_cls.create_from_data(init_map)
        for nested_name, nested_value in iteritems_(nested_map):
            set_nested_attribute(entity, nested_name, nested_value)
        return entity

    def __str__(self):
        return "%s(id=%s)" % (self._data.__class__.__name__,
                              self.get_id())


class DataElementDataTraversalProxyAdapter(DataTraversalProxyAdapter):
    proxy_class = DataElementDataTraversalProxy

    def make_source_proxy(self, options=None):
        rel_drct = RELATIONSHIP_DIRECTIONS.REVERSE
        if options is None:
            options = {}
        options['mapping'] = self._data.mapping
        return self.make_proxy(None, rel_drct, options)

    def make_target_proxy(self, accessor,
                          manage_back_references=True, options=None):
        rel_drct = RELATIONSHIP_DIRECTIONS.BIDIRECTIONAL
        if not manage_back_references:
            rel_drct &= ~RELATIONSHIP_DIRECTIONS.REVERSE
        return self.make_proxy(accessor, rel_drct, options=options)

    def make_proxy(self, accessor, relationship_direction, options=None):
        if ICollectionDataElement.providedBy(self._data): # pylint:disable=E1101
            reg = get_current_registry()
            prx_fac = reg.getUtility(IDataTraversalProxyFactory)
            prx = prx_fac.make_proxy(list(self._data.get_members()),
                                     accessor, relationship_direction,
                                     options=options)
        else:
            prx = DataTraversalProxyAdapter.make_proxy(self, accessor,
                                                       relationship_direction,
                                                       options=options)
        return prx
