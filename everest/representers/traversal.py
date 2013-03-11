"""
Resource data tree traversal.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 25, 2012.
"""
from collections import OrderedDict
from everest.entities.utils import get_entity_class
from everest.representers.attributes import AttributeKey
from everest.representers.config import IGNORE_ON_READ_OPTION
from everest.representers.config import IGNORE_ON_WRITE_OPTION
from everest.representers.config import WRITE_AS_LINK_OPTION
from everest.representers.interfaces import ICollectionDataElement
from everest.representers.interfaces import ILinkedDataElement
from everest.representers.interfaces import IMemberDataElement
from everest.resources.attributes import ResourceAttributeKinds
from everest.resources.descriptors import CARDINALITY
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.kinds import ResourceKinds
from everest.resources.staging import create_staging_collection
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_member_class
from everest.resources.utils import url_to_resource
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['DataElementBuilderResourceTreeVisitor',
           'DataElementTreeTraverser',
           'DataTreeTraverser',
           'DataElementTreeTraverser',
           'ResourceDataTreeTraverser',
           'ResourceBuilderDataElementTreeVisitor',
           'ResourceDataVisitor',
           'ResourceTreeTraverser',
           'PROCESSING_DIRECTIONS',
           ]


class PROCESSING_DIRECTIONS(object):
    """
    Constants specifying the direction resource data are processed.
    """
    #: Resource data are being read (i.e., a representation is converted
    #: to a resource.
    READ = 'READ'
    #: Resource data are being written (i.e., a resource is converted
    #: to a representation.
    WRITE = 'WRITE'


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
            for attr, value in member_data.iteritems():
                if attr.kind == ResourceAttributeKinds.TERMINAL:
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
        if attribute.kind == ResourceAttributeKinds.MEMBER:
            kind = ResourceKinds.MEMBER
            rc_cls = get_member_class(attribute.value_type)
        else:
            kind = ResourceKinds.COLLECTION
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


class ResourceBuilderDataElementTreeVisitor(ResourceDataVisitor):
    def __init__(self):
        ResourceDataVisitor.__init__(self)
        self.__resource = None

    def visit_member(self, attribute_key, attribute, member_node, member_data,
                     is_link_node, parent_data, index=None):
        if is_link_node:
            url = member_node.get_url()
            rc = url_to_resource(url)
            entity = rc.get_entity()
        else:
            entity_cls = get_entity_class(member_node.mapping.mapped_class)
            entity_data = {}
            nested_entity_data = {}
            for attr, value in member_data.iteritems():
                if '.' in attr.entity_name:
                    nested_entity_data[attr.entity_name] = value
                else:
                    entity_data[attr.entity_name] = value
            entity = entity_cls.create_from_data(entity_data)
            # Set nested attribute values.
            # FIXME: lazy loading of nested attributes is not supported.
            for nested_attr, value in nested_entity_data.iteritems():
                tokens = nested_attr.split('.')
                parent = reduce(getattr, tokens[:-1], entity)
                if not parent is None:
                    setattr(parent, tokens[-1], value)
        if not index is None:
            # Collection member. Store in parent data with index as key.
            parent_data[index] = entity
        elif len(attribute_key) == 0:
            # Top level. Store root entity and create resource.
            mapped_cls = member_node.mapping.mapped_class
            self.__resource = mapped_cls.create_from_entity(entity)
        else:
            # Nested member. Store in parent data with attribute as key.
            parent_data[attribute] = entity

    def visit_collection(self, attribute_key, attribute, collection_node,
                         collection_data, is_link_node, parent_data):
        if is_link_node:
            url = collection_node.get_url()
            coll = url_to_resource(url)
            entities = [mb.get_entity() for mb in coll]
        else:
            entities = []
            for item in sorted(collection_data.items()):
                entities.append(item[1])
        if len(attribute_key) == 0: # Top level.
            mapped_cls = collection_node.mapping.mapped_class
            self.__resource = create_staging_collection(mapped_cls)
            for ent in entities:
                self.__resource.create_member(ent)
        else:
            parent_data[attribute] = entities

    @property
    def resource(self):
        return self.__resource


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
        self._dispatch(AttributeKey(()), None, self.__root, None, visitor)

    def _traverse_collection(self, attr_key, attr, collection_node,
                             parent_data, visitor):
        is_link_node = self._is_link_node(collection_node, attr)
        collection_data = {}
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
    def __init__(self, root, mapping, direction, ignore_none_values=True):
        """
        :param direction: processing direction (read or write). One of the
            :class:`PROCESSING_DIRECTIONS` constant attributes.
        """
        DataTreeTraverser.__init__(self, root)
        self._mapping = mapping
        self._direction = direction
        self.__ignore_none_values = ignore_none_values

    def _traverse_member(self, attr_key, attr, member_node, parent_data,
                         visitor, index=None):
        member_data = OrderedDict()
        is_link_node = self._is_link_node(member_node, attr)
        # Ignore links for traversal.
        if not is_link_node:
            if not attr is None:
                node_type = get_member_class(attr.value_type)
            else:
                node_type = self._get_node_type(member_node)
            for mb_attr in self._mapping.attribute_iterator(node_type,
                                                            attr_key):
                ignore_opt = self._get_ignore_option(mb_attr)
                if self.__ignore_attribute(ignore_opt, mb_attr, attr_key):
                    continue
                if mb_attr.kind == ResourceAttributeKinds.TERMINAL:
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
                    nested_attr_key = attr_key + (mb_attr.name,)
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
        if self._direction == PROCESSING_DIRECTIONS.READ:
            opt = attr.options.get(IGNORE_ON_READ_OPTION)
        else:
            opt = attr.options.get(IGNORE_ON_WRITE_OPTION)
        return opt

    def __ignore_attribute(self, ignore_opt, attr, attr_key):
        # Rules for ignoring attributes:
        #  * always ignore when IGNORE_ON_XXX_OPTION is set to True;
        #  * always include when IGNORE_ON_XXX_OPTION is set to False;
        #  * also ignore member attributes when the length of the attribute
        #    key is > 0 or the cardinality is not MANYTOONE (this avoids
        #    traversing circular attribute definitions such as parent ->
        #    children -> parent);
        #  * also ignore collection attributes when the cardinality is
        #    not MANYTOMANY.
        do_ignore = ignore_opt
        if ignore_opt is None:
            if attr.kind == ResourceAttributeKinds.MEMBER:
                depth = len(attr_key) + 1 - attr_key.offset
                do_ignore = depth > 1 \
                            or attr.cardinality != CARDINALITY.MANYTOONE
            elif attr.kind == ResourceAttributeKinds.COLLECTION:
                do_ignore = attr.cardinality != CARDINALITY.MANYTOMANY
        return do_ignore


class DataElementTreeTraverser(ResourceDataTreeTraverser):
    """
    Traverser for data element trees.
    
    This traverser can be used both inbound during reading (data element 
    -> resource) and outbound during writing (resource -> data element).
    """
    def __init__(self, root, mapping,
                 direction=PROCESSING_DIRECTIONS.READ,
                 ignore_none_values=True):
        ResourceDataTreeTraverser.__init__(
                                    self, root, mapping, direction,
                                    ignore_none_values=ignore_none_values)

    def _dispatch(self, attr_key, attr, node, parent_data, visitor):
        ifcs = provided_by(node)
        if IMemberDataElement in ifcs:
            traverse_fn = self._traverse_member
        elif ICollectionDataElement in ifcs:
            traverse_fn = self._traverse_collection
        elif ILinkedDataElement in ifcs:
            kind = node.get_kind()
            if kind == ResourceKinds.MEMBER:
                traverse_fn = self._traverse_member
            else: # kind == ResourceKinds.COLLECTION
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
        if self._direction == PROCESSING_DIRECTIONS.READ:
            value = node.get_terminal(attr)
        else:
            value = node.get_terminal_converted(attr)
        return value

    def _get_node_nested(self, node, attr):
        return node.get_nested(attr)


class ResourceTreeTraverser(ResourceDataTreeTraverser):
    """
    Mapping traverser for resource trees.
    """
    def __init__(self, root, mapping,
                 direction=PROCESSING_DIRECTIONS.WRITE,
                 ignore_none_values=True):
        ResourceDataTreeTraverser.__init__(
                                    self, root, mapping, direction,
                                    ignore_none_values=ignore_none_values)

    def _dispatch(self, attr_key, attr, node, parent_data, visitor):
        ifcs = provided_by(node)
        if IMemberResource in ifcs:
            self._traverse_member(attr_key, attr, node, parent_data, visitor)
        elif ICollectionResource in ifcs:
            self._traverse_collection(attr_key, attr, node, parent_data,
                                      visitor)
        else:
            raise ValueError('Data must be a resource.')

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
