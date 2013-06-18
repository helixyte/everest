"""
Resource data tree traversal.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 25, 2012.
"""
from collections import OrderedDict
from everest.constants import ResourceAttributeKinds
from everest.constants import ResourceKinds
from everest.entities.attributes import \
                        get_domain_class_terminal_attribute_iterator
from everest.entities.utils import get_entity_class
from everest.representers.attributes import MappedAttributeKey
from everest.representers.config import IGNORE_ON_READ_OPTION
from everest.representers.config import IGNORE_ON_WRITE_OPTION
from everest.representers.config import WRITE_AS_LINK_OPTION
from everest.representers.config import WRITE_MEMBERS_AS_LINK_OPTION
from everest.representers.interfaces import ICollectionDataElement
from everest.representers.interfaces import ILinkedDataElement
from everest.representers.interfaces import IMemberDataElement
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.staging import create_staging_collection
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_member_class
from everest.resources.utils import url_to_resource
from everest.utils import get_nested_attribute
from everest.utils import set_nested_attribute
from functools import reduce as func_reduce
from pyramid.compat import iteritems_
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
            for attr, value in iteritems_(member_data):
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
    def __init__(self, resource=None):
        ResourceDataVisitor.__init__(self)
        self.__resource = resource
        self.__updating = not resource is None

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
            for attr, value in iteritems_(member_data):
                if '.' in attr.entity_name:
                    nested_entity_data[attr.entity_name] = value
                else:
                    entity_data[attr.entity_name] = value
#            if not self.__updating:
            entity = entity_cls.create_from_data(entity_data)
#            else:
#                entity = reduce(getattr, tuple(attribute_key),
#                                self.__resource).get_entity()
#                for attr, value in entity_data.iteritems():
#                    setattr(entity, attr, value)
            # Set nested attribute values.
            # FIXME: lazy loading of nested attributes is not supported.
            for nested_attr, value in iteritems_(nested_entity_data):
                tokens = nested_attr.split('.')
                parent = func_reduce(getattr, tokens[:-1], entity)
                if not parent is None:
                    setattr(parent, tokens[-1], value)
        if not index is None:
            # Collection member. Store in parent data with index as key.
            parent_data[index] = entity
        elif len(attribute_key) == 0:
            # Top level.
            if not self.__updating:
                # Store root entity and create resource.
                mapped_cls = member_node.mapping.mapped_class
                self.__resource = mapped_cls.create_from_entity(entity)
            else:
                self.__resource.update_from_entity(entity)
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
            if not self.__updating:
                mapped_cls = collection_node.mapping.mapped_class
                self.__resource = create_staging_collection(mapped_cls)
                for ent in entities:
                    self.__resource.create_member(ent)
            else:
                self.__resource.update_from_entities(entities)
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
                if mb_attr.should_ignore(ignore_opt, attr_key):
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
        if self._direction == PROCESSING_DIRECTIONS.READ:
            opt = attr.options.get(IGNORE_ON_READ_OPTION)
        else:
            opt = attr.options.get(IGNORE_ON_WRITE_OPTION)
        return opt


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
            raise ValueError('Can only traverse domain objects that '
                             'provide IMember or ICollection (key: %s).'
                             % str(attr_key))

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


class SourceTargetTreeTraverser(object):
    def __init__(self, source, target,
                 ignore_none_values=True):
        self.__source_root = source
        self.__target_root = target
        self._ignore_none_values = ignore_none_values

    def run(self, visitor):
        """
        Runs this traverser.
        """
        self._dispatch([], MappedAttributeKey(()), self.__source_root,
                       self.__target_root, visitor)

    def _dispatch(self, path, attr_key, source_node, target_node, visitor):
        raise NotImplementedError('Abstract method.')

    def _do_traverse(self, attr_key, source_node, target_node):
        raise NotImplementedError('Abstract method.')

    def _get_node_type(self, node):
        raise NotImplementedError('Abstract method.')

    def _get_attribute_iterator(self, element_type, attr_key):
        raise NotImplementedError('Abstract method.')

    def _do_dispatch(self, attr_key, source_node, target_node):
        raise NotImplementedError('Abstract method.')

    def _get_node_nested(self, node, attr):
        raise NotImplementedError('Abstract method.')

    def _get_node_members(self, node):
        raise NotImplementedError('Abstract method.')

    def _lookup_target(self, source_node):
        raise NotImplementedError('Abstract method.')

    def _traverse_node(self, path, attr_key, source_node, target_node,
                       visitor):
        if self._do_traverse(attr_key, source_node, target_node):
            if len(attr_key) > 0:
                attr = attr_key[-1]
                node_type = get_member_class(attr.value_type)
            else:
                node_type = self._get_node_type(source_node or target_node)
            for mb_attr in self._get_attribute_iterator(node_type, attr_key):
                attr_key.append(mb_attr)
                if self._do_dispatch(attr_key, source_node, target_node):
                    if not source_node is None:
                        attr_source = self._get_node_nested(source_node,
                                                            mb_attr)
                    else:
                        attr_source = None
                    if not target_node is None:
                        attr_target = self._get_node_nested(target_node,
                                                            mb_attr)
                    else:
                        attr_target = None
                    if attr_source is None and attr_target is None:
                        # If both source and target have None values, there is
                        # nothing to do.
                        continue
#                    if ignore_opt is False:
#                        # The offset in the attribute key ensures that
#                        # the defaults for ignoring attributes of the
#                        # nested attribute can be retrieved correctly.
#                        nested_attr_key.offset = len(nested_attr_key)
                    path.append((source_node, target_node))
                    self._dispatch(path, attr_key, attr_source, attr_target,
                                   visitor)
                    path.pop()
                attr_key.pop()
        visitor.visit_node(attr_key, source_node, target_node)
#                             is_link_node, parent_data,
#                             target_node=target_node, index=index)

    def _traverse_set(self, path, attr_key, source_set, target_set, visitor):
        source_ids = set()
        if self._do_traverse(attr_key, source_set, target_set):
            for source_node in self._get_node_members(source_set):
                source_id = source_node.id
                if not source_id is None:
                    source_ids.add(source_id)
                    if not target_set is None:
                        # if we find a target here: UPDATE else: CREATE
                        target_node = self._lookup_target(source_node)
                    else:
                        # CREATE
                        target_node = None
                else:
                    # CREATE
                    target_node = None
                self._traverse_node(path, attr_key, source_node,
                                    target_node, visitor)
        if not target_set is None:
            for target_node in target_set:
                if target_node.id in source_ids:
                    continue
                # DELETE
                self._traverse_node(path, attr_key, None, target_node,
                                    visitor)
        visitor.visit_set(path, attr_key, source_set, target_set)


class SourceTargetDataElementTreeTraverser(SourceTargetTreeTraverser):
    def __init__(self, source, target, mapping,
                 direction=PROCESSING_DIRECTIONS.READ,
                 **kw):
        SourceTargetTreeTraverser.__init__(self, source, target, **kw)
        self._mapping = mapping
        self._direction = direction

    def _dispatch(self, path, attr_key, source, target, visitor):
        ifcs = provided_by(source or target)
        if IMemberResource in ifcs:
            self._traverse_node(path, attr_key, source, target, visitor)
        elif ICollectionResource in ifcs:
            self._traverse_set(path, attr_key, source, target, visitor)
        else:
            raise ValueError('Can only traverse domain objects that '
                             'provide IMember or ICollection (key: %s).'
                             % str(attr_key))

    def _do_traverse(self, attr_key, source_node, target_node):
        return self._is_link_node(attr_key[-1])

    def _do_dispatch(self, attr_key, source_node, target_node):
        ignore_opt = self._get_ignore_option(attr_key[-1])
        return not attr_key[-1].should_ignore(ignore_opt, attr_key)

    def _lookup_target(self, source_node):
        coll = source_node.get_root_collection()
        return coll[source_node.slug]

    def _get_attribute_iterator(self, element_type, attr_key):
        return self._mapping.nonterminal_attribute_iterator(
                                                    mapped_class=element_type,
                                                    key=attr_key)

    def _get_node_type(self, node):
        return type(node)

    def _get_node_terminal(self, node, attr):
        return getattr(node, attr.name)

    def _get_node_nested(self, node, attr):
        return getattr(node, attr.name)

    def _get_node_members(self, node):
        return iter(node)

    def _is_link_node(self, attr):
        return not attr is None and \
               not attr.options.get(WRITE_AS_LINK_OPTION) is False

    def _get_ignore_option(self, attr):
        if self._direction == PROCESSING_DIRECTIONS.READ:
            opt = attr.options.get(IGNORE_ON_READ_OPTION)
        else:
            opt = attr.options.get(IGNORE_ON_WRITE_OPTION)
        return opt


class CrudResourceVisitor(object):
    def __init__(self, session, aggregate_factory):
        self.__session = session
        self.__agg_fac = aggregate_factory

    def visit_node(self, path, attribute, source_data_element,
                   target_resource):
        if attribute is None:
            # Visiting the root.
            entity_class = get_entity_class(target_resource)
        else:
            entity_class = get_entity_class(attribute.attr_type)
#        if target_entity is None and not source_entity.id is None:
#            # Try to load the target entity if we have an ID.
#            agg = self.__agg_fac(source_entity)
#            target_entity = agg.get_by_id(source_entity.id)
        if source_data_element is None or target_resource is None:
            if attribute is None:
                relationship = None
            else:
                if source_data_element is None:
                    parent = path[-1][1]
                else:
                    parent = path[-1][0]
                relationship = attribute.make_relationship(parent)
            if target_resource is None:
                self.__create(source_data_element, entity_class,
                              relationship=relationship)
            else:
                self.__delete(target_resource, entity_class,
                              relationship=relationship)
        else:
            self.__update(entity_class, source_data_element, target_resource)

    def visit_set(self, path, attr, source_aggregate, target_aggregate):
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
