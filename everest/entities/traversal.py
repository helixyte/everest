"""
Entity tree traversal operations.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 8, 2013.
"""
from everest.constants import RELATIONSHIP_DIRECTIONS
from everest.constants import RELATION_OPERATIONS
from everest.entities.attributes import get_domain_class_attribute_iterator
from everest.entities.relationship import LazyDomainRelationship
from everest.entities.utils import get_entity_class
from everest.interfaces import IDataTraversalProxyFactory
from everest.resources.interfaces import ICollectionResource
from everest.resources.utils import url_to_resource
from everest.traversal import DataTraversalProxy
from everest.traversal import DataTraversalProxyAdapter
from everest.utils import get_nested_attribute
from pyramid.threadlocal import get_current_registry

__docformat__ = 'reStructuredText en'
__all__ = ['AruVisitor',
           'DomainDataTraversalProxy',
           'DomainDataTraversalProxyAdapter',
           'LinkedDomainDataTraversalProxy',
           'LinkedDomainDataTraversalProxyAdapter',
           'ResourceDataTreeVisitor',
           ]


class ResourceDataTreeVisitor(object):
    """
    Abstract base class for resource data tree traversal visitors.
    """
    def __init__(self, rc_class):
        self._rc_class = rc_class

    def prepare(self):
        """
        Prepare the visitor for traversal.

        Called by the traverser; override to implement functionality needed
        to prepare the visitor for a new resource tree traversal operation.
        """
        pass #pragma: no cover

    def finalize(self):
        """
        Finalize the visitor after traversal.

        Called by the traverser; override to implement functionality the
        visitor needs to run ''after'' traversal of the full resource tree
        has finished.
        """
        pass #pragma: no cover

    def visit(self, path, attribute, source, target):
        """
        Visits a single node in the resource data tree.

        The relation operation for the visit can be determined implicitly from
        the values of the :param:`source` and :param:`target` parameters:
        REMOVE if only :param:`source` is `None`, ADD if only :param:`target`,
        and UPDATE if both are not `None`.

        :param path: Traversal path.
        :param attribute: Resource attribute to traverse. This is `None` for
          nodes at the root of the tree.
        :param source: Traversal proxy for source data.
        :param target: Traversal proxy for target data.
        """
        raise NotImplementedError('Abstract method.')


class AruVisitor(ResourceDataTreeVisitor):
    """
    Add-Remove-Update visitor for resource data tree traversal.
    """
    class Callback(object):
        operation = None
        def __init__(self, method, args):
            self.method = method
            self.args = args

        def __call__(self):
            self.method(*self.args)

        def __str__(self):
            return "%s: %s (%d)" \
                   % (self.operation, self.args[1], len(self.args[-1])) #pragma: no cover

    class AddCallback(Callback):
        operation = 'ADD'

    class RemoveCallback(Callback):
        operation = 'REMOVE'

    class UpdateCallback(Callback):
        operation = 'UPDATE'

    def __init__(self, rc_class, add_callback=None, remove_callback=None,
                 update_callback=None, pass_path_to_callbacks=False):
        ResourceDataTreeVisitor.__init__(self, rc_class)
        self.__add_callback = add_callback
        self.__remove_callback = remove_callback
        self.__update_callback = update_callback
        self.__pass_path_to_callbacks = pass_path_to_callbacks
        self.__commands = None
        self.root = None

    def prepare(self):
        #: The root of the new source tree (ADD) or of the updated target
        #: tree (UPDATE) or the removed entity (REMOVE).
        self.root = None
        #
        self.__commands = []

    def visit(self, path, attribute, source, target):
        is_root = attribute is None
        if is_root:
            # Visiting the root.
            ent_class = get_entity_class(self._rc_class)
        else:
            ent_class = get_entity_class(attribute.attr_type)
            parent = path.parent
        if source is None:
            # No source - REMOVE.
            entity = target.get_entity()
            if not is_root:
                rel = self.__get_relationship(parent, attribute)
                rel.remove(entity)
            if not self.__remove_callback is None:
                if self.__pass_path_to_callbacks:
                    args = (ent_class, entity, path)
                else:
                    args = (ent_class, entity)
                cmd = self.RemoveCallback(self.__remove_callback, args)
                self.__commands.append(cmd)
        else:
            if target is None:
                # No target - ADD.
                entity = source.get_entity()
                if not is_root:
                    if path.relation_operation == RELATION_OPERATIONS.ADD:
                        # If the parent is created new, the constructor
                        # will most likely set the child attribute.
                        add_opts = dict(safe=True)
                    else:
                        add_opts = dict()
                    rel = self.__get_relationship(parent, attribute)
                    rel.add(entity, **add_opts)
                if not self.__add_callback is None:
                    if self.__pass_path_to_callbacks:
                        args = (ent_class, entity, path)
                    else:
                        args = (ent_class, entity)
                    cmd = self.AddCallback(self.__add_callback, args)
                    self.__commands.append(cmd)
            else:
                # Both source and target - UPDATE.
                entity = target.get_entity()
                if not self.__update_callback is None:
                    upd_av_map = dict(source.update_attribute_value_items)
                    if self.__pass_path_to_callbacks:
                        args = (ent_class, upd_av_map, entity, path)
                    else:
                        args = (ent_class, upd_av_map, entity)
                    cmd = self.UpdateCallback(self.__update_callback, args)
                    self.__commands.append(cmd)
                if not is_root:
                    # The relationship with the old value has already been
                    # severed, so we only need to ADD here.
                    rel = self.__get_relationship(parent, attribute)
                    rel.add(entity)
        if is_root:
            self.root = entity
        else:
            self.__commands.append(rel)

    def finalize(self):
        for cmd in self.__commands:
            cmd()

    def __get_relationship(self, proxy, attribute):
        try:
            rel = proxy.get_relationship(attribute)
        except KeyError:
            rel = LazyDomainRelationship(
                                proxy, attribute,
                                direction=proxy.relationship_direction)
            proxy.set_relationship(attribute, rel)
        return rel


class DomainDataTraversalProxy(DataTraversalProxy):
    def get_id(self):
        return self._data.id

    def _get_entity_type(self):
        return type(self._data)

    def get_entity(self):
        return self._data

    def _attribute_iterator(self):
        it = get_domain_class_attribute_iterator(self._data)
        for attr in it:
            if not attr.entity_attr is None:
                yield attr

    def _get_relation_attribute_value(self, attribute):
        return get_nested_attribute(self._data, attribute.entity_attr)

    def _get_proxied_attribute_value(self, attribute):
        return get_nested_attribute(self._data, attribute.entity_attr)

    def _make_accessor(self, value_type):
        return self._accessor.get_root_aggregate(value_type)


class DomainDataTraversalProxyAdapter(DataTraversalProxyAdapter):
    proxy_class = DomainDataTraversalProxy

    def make_source_proxy(self, options=None):
        rel_drct = RELATIONSHIP_DIRECTIONS.NONE
        return self.make_proxy(None, rel_drct, options=options)

    def make_target_proxy(self, accessor,
                          manage_back_references=True, options=None):
        rel_drct = RELATIONSHIP_DIRECTIONS.BIDIRECTIONAL
        if not manage_back_references:
            rel_drct &= ~RELATIONSHIP_DIRECTIONS.REVERSE
        return self.make_proxy(accessor, rel_drct, options=options)


class LinkedDomainDataTraversalProxy(DomainDataTraversalProxy):
    def do_traverse(self):
        return False

    def __str__(self):
        return "Linked%s" % DomainDataTraversalProxy.__str__(self)


class LinkedDomainDataTraversalProxyAdapter(DomainDataTraversalProxyAdapter):
    proxy_class = LinkedDomainDataTraversalProxy

    def make_target_proxy(self, accessor,
                          manage_back_references=True, options=None):
        raise NotImplementedError('Not implemented.')

    def make_proxy(self, accessor, relationship_direction, options=None):
        # Note: We ignore the options; if something was passed here,
        #       it came from a parent data element data traversal proxy.
        url = self._data.get_url()
        rc = url_to_resource(url)
        if ICollectionResource.providedBy(rc): # pylint:disable=E1101
            reg = get_current_registry()
            prx_fac = reg.getUtility(IDataTraversalProxyFactory)
            prx = prx_fac.make_proxy([mb.get_entity() for mb in rc],
                                     accessor, relationship_direction)
        else:
            prx = LinkedDomainDataTraversalProxy(rc.get_entity(),
                                                 accessor,
                                                 relationship_direction)
        return prx

