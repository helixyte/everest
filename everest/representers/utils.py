"""
Representer related utilities.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 18, 2011.
"""
from everest.representers.interfaces import ICollectionDataElement
from everest.representers.interfaces import ILinkedDataElement
from everest.representers.interfaces import IRepresenterRegistry
from everest.representers.interfaces import IResourceDataElement
from pyramid.compat import NativeIO
from pyramid.compat import iteritems_
from pyramid.threadlocal import get_current_registry
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
import os

__docformat__ = 'reStructuredText en'
__all__ = ['NewRepresenterConfigurationContext',
           'UpdatedRepresenterConfigurationContext',
           'as_representer',
           'data_element_tree_to_string',
           'get_mapping_registry',
           ]


def as_representer(resource, content_type):
    """
    Adapts the given resource and content type to a representer.

    :param resource: resource to adapt.
    :param str content_type: content (MIME) type to obtain a representer for.
    """
    reg = get_current_registry()
    rpr_reg = reg.queryUtility(IRepresenterRegistry)
    return rpr_reg.create(type(resource), content_type)


def get_mapping_registry(content_type):
    """
    Returns the data element registry for the given content type (a Singleton).

    :Note: This only works after a representer for the given content type
        has been created.
    """
    reg = get_current_registry()
    rpr_reg = reg.queryUtility(IRepresenterRegistry)
    return rpr_reg.get_mapping_registry(content_type)


def data_element_tree_to_string(data_element):
    """
    Creates a string representation of the given data element tree.
    """
    # FIXME: rewrite this as a visitor to use the data element tree traverser.
    def __dump(data_el, stream, offset):
        name = data_el.__class__.__name__
        stream.write("%s%s" % (' ' * offset, name))
        offset += 2
        ifcs = provided_by(data_el)
        if ICollectionDataElement in ifcs:
            stream.write("[")
            first_member = True
            for member_data_el in data_el.get_members():
                if first_member:
                    stream.write('%s' % os.linesep + ' ' * offset)
                    first_member = False
                else:
                    stream.write(',%s' % os.linesep + ' ' * offset)
                __dump(member_data_el, stream, offset)
            stream.write("]")
        else:
            stream.write("(")
            if ILinkedDataElement in ifcs:
                stream.write("url=%s, kind=%s, relation=%s" %
                             (data_el.get_url(), data_el.get_kind(),
                              data_el.get_relation()))
            else:
                first_attr = True
                for attr_name, attr_value in iteritems_(data_el.data):
                    if first_attr:
                        first_attr = False
                    else:
                        stream.write(',%s' % os.linesep
                                     + ' ' * (offset + len(name) + 1))
                    if attr_value is None:
                        continue
                    if not IResourceDataElement in provided_by(attr_value):
                        stream.write("%s=%s" % (attr_name, attr_value))
                    else:
                        stream.write("%s=" % attr_name)
                        __dump(attr_value, stream, offset)
            stream.write(')')
    stream = NativeIO()
    __dump(data_element, stream, 0)
    return stream.getvalue()


class _RepresenterConfigurationContext(object):
    """
    Base class for context managers that configure a representer.

    :ivar options: The representer options map to use within the context.
    :ivar attribute_options: The representer attribute options map to use
      within the context.
    """
    def __init__(self, mapped_class, content_type,
                 options=None, attribute_options=None):
        self.options = options
        self.attribute_options = attribute_options
        self.__mapped_class = mapped_class
        self.__content_type = content_type
        self.__mapping = None

    def __enter__(self):
        mp_reg = get_mapping_registry(self.__content_type)
        self.__mapping = mp_reg.find_or_create_mapping(self.__mapped_class)
        cfg = self._make_configuration(self.__mapping.configuration,
                                          self.options,
                                          self.attribute_options)
        self.__mapping.push_configuration(cfg)

    def __exit__(self, ext_type, value, tb):
        self.__mapping.pop_configuration()

    def _make_configuration(self, current_configuration, options,
                            attribute_options):
        raise NotImplementedError('Abstract method.')


class NewRepresenterConfigurationContext(_RepresenterConfigurationContext):
    """
    A context manager that configures a representer with a newly created
    configuration.
    """
    def _make_configuration(self, current_configuration,
                               options, attribute_options):
        cfg_cls = type(current_configuration)
        cfg = cfg_cls(options=options, attribute_options=attribute_options)
        return cfg


class UpdatedRepresenterConfigurationContext(
                                        _RepresenterConfigurationContext):
    """
    A context manager that configures a representer with a copied and updated
    configuration.
    """
    def _make_configuration(self, current_configuration,
                               options, attribute_options):
        new_cfg = current_configuration.copy()
        upd_cfg = type(new_cfg)(options=options,
                                attribute_options=attribute_options)
        new_cfg.update(upd_cfg)
        return new_cfg
