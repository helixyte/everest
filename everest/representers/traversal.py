"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 25, 2012.
"""
from collections import OrderedDict
from everest.entities.utils import get_entity_class
from everest.representers.config import IGNORE_ON_READ_OPTION
from everest.representers.config import IGNORE_ON_WRITE_OPTION
from everest.representers.config import WRITE_AS_LINK_OPTION
from everest.representers.interfaces import ICollectionDataElement
from everest.representers.interfaces import ILinkedDataElement
from everest.representers.interfaces import IMemberDataElement
from everest.representers.urlloader import LazyUrlLoader
from everest.resources.attributes import ResourceAttributeKinds
from everest.resources.descriptors import CARDINALITY
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.kinds import ResourceKinds
from everest.resources.utils import new_stage_collection
from everest.url import url_to_resource
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = []


class ResourceDataVisitor(object):
    def visit_member(self, attribute_key, attribute, member_node, member_data,
                     parent_data, index=None):
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
          extracted during traversal (with mapped attributes as keys). This
          will be empty during pre-order visits.
        :param dict parent_data: dictionary holding all parent data extracted
          during traversal (with mapped attributes as keys).
        :param int index: this indicates a member node's index in a collection
          parent node. If the parent node is a member node, it will be `None`.
        """
        raise NotImplementedError('Abstract method.')

    def visit_collection(self, attribute_key, attribute, collection_node,
                         parent_data):
        """
        Visits a collection node in a resource data tree.
        
        :param tuple attribute_key: tuple containing the attribute tokens
          identifying the collection node's position in the resource data 
          tree.
        :param attribute: mapped attribute holding information about the
          collection node's name (in the parent) and type etc.
        :type attribute:
          :class:`everest.representers.attributes.MappedAttribute`
        :param dict parent_data: dictionary holding all parent data extracted
          during traversal (with mapped attributes as keys).
        """
        raise NotImplementedError('Abstract method.')


class DataElementBuilderResourceTreeVisitor(ResourceDataVisitor):
    def __init__(self, mapping):
        ResourceDataVisitor.__init__(self)
        self.__mapping = mapping
        self.__data = {}

    def visit_member(self, attribute_key, attribute, member_node, member_data,
                     parent_data, index=None):
        if not attribute is None and \
           not attribute.options.get(WRITE_AS_LINK_OPTION) is False:
            mb_data_el = self.__write_link(member_node)
        else:
            mb_data_el = \
                self.__mapping.create_data_element_from_resource(member_node)
            # Process terminal attributes.
            for attr, value in member_data.iteritems():
                if attr.kind == ResourceAttributeKinds.TERMINAL:
                    mb_data_el.set_terminal(attr, value)
                else:
                    mb_data_el.set_nested(attr, value)
        if not index is None:
            # Member of a collection. Store with indexed key.
            self.__data[attribute_key + (index,)] = mb_data_el
        elif attribute_key == ():
            # Top level - store root data element.
            self.__data[()] = mb_data_el
        else:
            # Nested member. Store in parent data.
            parent_data[attribute] = mb_data_el

    def visit_collection(self, attribute_key, attribute, collection_node,
                         parent_data):
        if not attribute is None and \
           attribute.options.get(WRITE_AS_LINK_OPTION) is True:
            coll_data_el = self.__write_link(collection_node)
        else:
            coll_data_el = \
              self.__mapping.create_data_element_from_resource(collection_node)
            for idx in range(len(collection_node)):
                mb_data_el = self.__data[attribute_key + (idx,)]
                coll_data_el.add_member(mb_data_el)
        if attribute_key == (): # Top level.
            self.__data[()] = coll_data_el
        else:
            parent_data[attribute] = coll_data_el

    @property
    def data_element(self):
        return self.__data.get(())

    def __write_link(self, resource):
        return \
            self.__mapping.create_linked_data_element_from_resource(resource)


class ResourceBuilderDataElementTreeVisitor(ResourceDataVisitor):
    def __init__(self, resolve_urls=True):
        ResourceDataVisitor.__init__(self)
        self.__resolve_urls = resolve_urls
        self.__data = dict()
        self.__resource = None

    def visit_member(self, attribute_key, attribute, member_node, member_data,
                     parent_data, index=None):
        if ILinkedDataElement in provided_by(member_node):
            entity = self.__extract_link(member_node)
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
            for nested_attr, value in nested_entity_data.iteritems():
                tokens = nested_attr.split('.')
                parent = reduce(getattr, tokens[:-1], entity)
                setattr(parent, tokens[-1], value)
        if not index is None:
            # Collection member. Store with indexed key.
            self.__data[attribute_key + (index,)] = entity
        elif attribute_key == ():
            # Top level. Store root entity and create resource.
            self.__data[()] = entity
            mapped_cls = member_node.mapping.mapped_class
            self.__resource = mapped_cls.create_from_entity(entity)
        else:
            # Nested member. Store in parent data.
            parent_data[attribute] = entity

    def visit_collection(self, attribute_key, attribute, collection_node,
                         parent_data):
        if ILinkedDataElement in provided_by(collection_node):
            entities = self.__extract_link(collection_node)
        else:
            entities = []
            for idx in range(len(collection_node)):
                entity = self.__data[attribute_key + (idx,)]
                entities.append(entity)
        if attribute_key == (): # Top level.
            self.__data[attribute_key] = entities
            mapped_cls = collection_node.mapping.mapped_class
            self.__resource = new_stage_collection(mapped_cls)
            for ent in entities:
                self.__resource.create_member(ent)
        else:
            parent_data[attribute] = entities

    def __extract_link(self, linked_data_el):
        url = linked_data_el.get_url()
        if self.__resolve_urls:
            rc = url_to_resource(url)
            if IMemberResource in provided_by(rc):
                rc_data = rc.get_entity()
            else:
                rc_data = [mb.get_entity() for mb in rc]
        else:
            rc_data = LazyUrlLoader(url, url_to_resource)
        return rc_data

    @property
    def resource(self):
        return self.__resource


class ResourceDataTreeTraverser(object):
    """
    Traverser for a resource data tree.
    """
    def __init__(self, mapping, root, visit_pre=False, visit_post=True):
        self._mapping = mapping
        self.__root = root
        self.__visit_pre = visit_pre
        self.__visit_post = visit_post

    def run(self, visitor):
        """
        Runs this traverser.
        """
        self._dispatch((), None, self.__root, None, visitor)

    def run_post_order(self, visitor):
        self.__visit_pre = False
        self.__visit_post = True
        self._dispatch((), None, self.__root, None, visitor)

    def run_pre_order(self, visitor):
        self.__visit_pre = True
        self.__visit_post = False
        self._dispatch((), None, self.__root, None, visitor)

    def _traverse_member(self, attr_key, attr, member_node, parent_data,
                         visitor, index=None):
        member_data = OrderedDict()
        if self.__visit_pre:
            visitor.visit_member(attr_key, attr, member_node, member_data,
                                 parent_data, index=index)
        if not self._ignore_node(member_node, attr):
            node_type = self._get_type_from_node(member_node)
            for mb_attr in self._mapping.attribute_iterator(node_type,
                                                            attr_key):
                if self.__ignore_attribute(mb_attr, attr_key):
                    continue
                if mb_attr.kind == ResourceAttributeKinds.TERMINAL:
                    # Terminal attribute - extract.
                    value = self._get_node_terminal(member_node, mb_attr)
                    if value is None:
                        # None values are ignored.
                        continue
                    member_data[mb_attr] = value
                else:
                    # Nested attribute - traverse.
                    nested_node = self._get_node_nested(member_node, mb_attr)
                    if nested_node is None:
                        # Stop condition - the given data element does not
                        # contain a nested attribute of the given mapped name.
                        continue
                    nested_attr_key = attr_key + (mb_attr.name,)
                    self._dispatch(nested_attr_key, mb_attr, nested_node,
                                   member_data, visitor)
        if self.__visit_post:
            visitor.visit_member(attr_key, attr, member_node, member_data,
                                 parent_data, index=index)

    def _traverse_collection(self, attr_key, attr, collection_node,
                             parent_data, visitor):
        if self.__visit_pre:
            visitor.visit_collection(attr_key, attr, collection_node,
                                     parent_data)
        if not self._ignore_node(collection_node, attr):
            all_mb_nodes = self._get_node_members(collection_node)
            for idx, mb_node in enumerate(all_mb_nodes):
                self._traverse_member(attr_key, attr, mb_node, parent_data,
                                      visitor, index=idx)
        if self.__visit_post:
            visitor.visit_collection(attr_key, attr, collection_node,
                                     parent_data)

    def _dispatch(self, attr_key, attr, node, parent_data, visitor):
        raise NotImplementedError('Abstract method.')

    def _get_type_from_node(self, node):
        raise NotImplementedError('Abstract method.')

    def _get_node_terminal(self, node, attr):
        raise NotImplementedError('Abstract method.')

    def _get_node_nested(self, node, attr):
        raise NotImplementedError('Abstract method.')

    def _get_node_members(self, node):
        raise NotImplementedError('Abstract method.')

    def _ignore_node(self, node, attr):
        raise NotImplementedError('Abstract method.')

    def _get_ignore_option(self, attr):
        raise NotImplementedError('Abstract method.')

    def __ignore_attribute(self, attr, attr_key):
        # Rules for ignoring attributes:
        #  * always ignore when IGNORE_ON_XXX_OPTION is set to True
        #  * always include when IGNORE_ON_XXX_OPTION is set to False
        #  * also ignore member attributes when the length of the attribute
        #    key is > 1 or the cardinality is not MANYTOONE
        #  * also ignore collection attributes when the length of the 
        #    attribute key is > 1 or the cardinality is not MANYTOMANY
        do_ignore = self._get_ignore_option(attr)
        if do_ignore is None:
            if attr.kind == ResourceAttributeKinds.MEMBER:
                do_ignore = len(attr_key) > 1 \
                            or attr.cardinality != CARDINALITY.MANYTOONE
            elif attr.kind == ResourceAttributeKinds.COLLECTION:
                do_ignore = len(attr_key) > 1 \
                            or attr.cardinality != CARDINALITY.MANYTOMANY
        return do_ignore


class DataElementTreeTraverser(ResourceDataTreeTraverser):
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
            elif kind == ResourceKinds.COLLECTION:
                traverse_fn = self._traverse_collection
            else:
                raise ValueError('Invalid resource kind "%s".' % kind)
        else:
            raise ValueError('Need MEMBER or COLLECTION data element; found '
                             '"%s".' % node)
        traverse_fn(attr_key, attr, node, parent_data, visitor)

    def _get_type_from_node(self, node):
        return node.mapping.mapped_class

    def _get_node_terminal(self, node, attr):
        return node.get_terminal(attr)

    def _get_node_nested(self, node, attr):
        return node.get_nested(attr)

    def _get_node_members(self, node):
        return node.get_members()

    def _ignore_node(self, node, attr):
        return ILinkedDataElement in provided_by(node)

    def _get_ignore_option(self, attr):
        return attr.options.get(IGNORE_ON_READ_OPTION)


class ResourceTreeTraverser(ResourceDataTreeTraverser):
    def _dispatch(self, attr_key, attr, node, parent_data, visitor):
        ifcs = provided_by(node)
        if IMemberResource in ifcs:
            self._traverse_member(attr_key, attr, node, parent_data, visitor)
        elif ICollectionResource in ifcs:
            self._traverse_collection(attr_key, attr, node, parent_data,
                                      visitor)
        else:
            raise ValueError('Data must be a resource.')

    def _get_type_from_node(self, node):
        return type(node)

    def _get_node_terminal(self, node, attr):
        return getattr(node, attr.name)

    def _get_node_nested(self, node, attr):
        return getattr(node, attr.name)

    def _get_node_members(self, node):
        return iter(node)

    def _ignore_node(self, node, attr):
        return not attr is None and \
               attr.options.get(WRITE_AS_LINK_OPTION) is True

    def _get_ignore_option(self, attr):
        return attr.options.get(IGNORE_ON_WRITE_OPTION)