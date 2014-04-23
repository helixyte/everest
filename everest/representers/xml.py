"""
XML representers.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 19, 2011.
"""
from collections import OrderedDict
import datetime

from lxml import etree
from lxml import objectify
from pkg_resources import resource_filename # pylint: disable=E0611
from pyramid.compat import bytes_
from pyramid.compat import text_type

from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.constants import RESOURCE_KINDS
from everest.mime import XmlMime
from everest.representers.base import MappingResourceRepresenter
from everest.representers.base import RepresentationGenerator
from everest.representers.base import RepresentationParser
from everest.representers.config import RepresenterConfiguration
from everest.representers.converters import BooleanConverter
from everest.representers.converters import ConverterRegistry
from everest.representers.converters import DateTimeConverter
from everest.representers.dataelements import CollectionDataElement
from everest.representers.dataelements import LinkedDataElement
from everest.representers.dataelements import MemberDataElement
from everest.representers.interfaces import ILinkedDataElement
from everest.representers.mapping import MappingRegistry
from everest.representers.utils import get_mapping_registry
from everest.resources.link import Link
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_member_class
from everest.resources.utils import provides_member_resource
from everest.resources.utils import resource_to_url
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['XmlCollectionDataElement',
           'XmlConverterRegistry',
           'XmlLinkedDataElement',
           'XmlMappingRegistry',
           'XmlMemberDataElement',
           'XmlParserFactory',
           'XmlRepresentationGenerator',
           'XmlRepresentationParser',
           'XmlRepresenterConfiguration',
           'XmlResourceRepresenter',
           ]


XML_NS_OPEN_SEARCH = 'http://a9.com/-/spec/opensearch/1.1/'
XML_NS_XSI = 'http://www.w3.org/2001/XMLSchema-instance'

XML_TAG_OPTION = 'xml_tag'
XML_SCHEMA_OPTION = 'xml_schema'
XML_NAMESPACE_OPTION = 'xml_ns'
XML_PREFIX_OPTION = 'xml_prefix'
XML_VALIDATE_OPTION = 'xml_validate'

NAMESPACE_MAPPING_OPTION = 'namespace'


class XmlConverterRegistry(ConverterRegistry):
    pass

XmlConverterRegistry.register(datetime.datetime, DateTimeConverter)
XmlConverterRegistry.register(bool, BooleanConverter)


class XmlRepresentationParser(RepresentationParser):
    def run(self):
        # Create an XML schema.
        schema_loc = self.get_option('schema_location')
        parser = XmlParserFactory.create(schema_location=schema_loc)
        try:
            tree = objectify.parse(self._stream, parser)
        except etree.XMLSyntaxError as err:
            msg = 'Could not parse XML document'
            if not schema_loc is None:
                msg += ' for schema %s.' % schema_loc
            raise SyntaxError('%s\n%s' % (msg, err.msg))
        return tree.getroot()[0]


class XmlRepresentationGenerator(RepresentationGenerator):
    def run(self, data_element):
        objectify.deannotate(data_element)
        etree.cleanup_namespaces(data_element)
        rpr_text = etree.tostring(data_element,
                                  pretty_print=True,
                                  encoding=text_type)
        self._stream.write(rpr_text)


class XmlParserFactory(object):
    __parser = None

    @classmethod
    def create(cls, schema_location=None):
        if not schema_location is None:
            schema = cls.__get_xml_schema(schema_location)
            parser = objectify.makeparser(schema=schema)
        else:
            parser = objectify.makeparser()
        # Get the class lookup from the mapping registry.
        mp_reg = get_mapping_registry(XmlMime)
        parser.set_element_class_lookup(mp_reg.parsing_lookup)
        return parser

    @classmethod
    def __get_xml_schema(cls, xml_schema_path):
        try:
            doc = etree.parse(resource_filename(*xml_schema_path.split(':')))
        except etree.XMLSyntaxError as err:
            raise SyntaxError('Could not parse XML schema %s.\n%s' %
                              (xml_schema_path, err.msg))
        try:
            schema = etree.XMLSchema(doc)
        except etree.XMLSchemaParseError as err:
            raise SyntaxError('Invalid XML schema.\n Parser message: %s'
                              % str(err))
        return schema


class XmlResourceRepresenter(MappingResourceRepresenter):
    content_type = XmlMime

    __tmpl = "<?xml version='1.0' encoding='%s' ?>%s"

    def to_bytes(self, obj, encoding=None):
        """
        Overwritten so we can insert the `?xml` processing directive.
        """
        if encoding is None:
            encoding = self.encoding
        text = self.__tmpl % (encoding, self.to_string(obj))
        return bytes_(text, encoding=encoding)

    def data_to_bytes(self, data_element, encoding=None):
        """
        Overwritten so we can insert the `?xml` processing directive.
        """
        if encoding is None:
            encoding = self.encoding
        text = self.__tmpl % (encoding, self.data_to_string(data_element))
        return bytes_(text, encoding=encoding)

    @classmethod
    def make_mapping_registry(cls):
        return XmlMappingRegistry()

    def _make_representation_parser(self, stream, resource_class, mapping):
        parser = XmlRepresentationParser(stream, resource_class, mapping)
        mp = self._mapping
        do_validate = mp.configuration.get_option(XML_VALIDATE_OPTION)
        if do_validate:
            xml_schema = mp.configuration.get_option(XML_SCHEMA_OPTION)
        else:
            xml_schema = None
        parser.set_option('schema_location', xml_schema)
        return parser

    def _make_representation_generator(self, stream, resource_class, mapping):
        return XmlRepresentationGenerator(stream, resource_class, mapping)


class _XmlDataElementMixin(object):
    @classmethod
    def create(cls, ns_map=None):
        return cls._create(ns_map)

    @classmethod
    def create_from_resource(cls, resource, ns_map=None): # ignore resource pylint:disable=W0613,W0221
        return cls._create(ns_map)

    @classmethod
    def _create(cls, ns_map):
        if ns_map is None:
            mp_reg = get_mapping_registry(XmlMime)
            ns_map = mp_reg.namespace_map
        cls_xml_tag = cls.mapping.configuration.get_option(XML_TAG_OPTION)
        if cls_xml_tag is None:
            raise ValueError('No XML tag registered for mapped class '
                             '%s.' % cls.mapping.mapped_class)
        cls_xml_ns = \
                cls.mapping.configuration.get_option(XML_NAMESPACE_OPTION)
        if not cls_xml_ns is None:
            tag = "{%s}%s" % (cls_xml_ns, cls_xml_tag)
            # FIXME: is this really necessary?
            ns_map[None] = cls_xml_ns
        else:
            tag = cls_xml_tag
        el_fac = XmlParserFactory.create().makeelement
        return el_fac(tag, nsmap=ns_map)


class XmlMemberDataElement(objectify.ObjectifiedElement,
                           _XmlDataElementMixin, MemberDataElement):
    #: This is used to identify nested attributes with None value.
    __NONE_MARKER = '__none__'
    converter_registry = XmlConverterRegistry

    def get_nested(self, attr):
        return self.__get_attribute(attr, True)

    def set_nested(self, attr, data_element):
        self.__set_attribute(attr, data_element)

    def get_terminal(self, attr):
        return self.__get_attribute(attr, True)

    def set_terminal(self, attr, value):
        self.__set_attribute(attr, value)

    def iterator(self):
        id_val = self.get('id')
        yield ('id', None) if id_val is None \
            else ('id', self.mapping.get_attribute('id').value_type(id_val))
        for child in self.iterchildren():
            idx = child.tag.find('}')
            if idx != -1:
                tag = child.tag[idx + 1:]
            else:
                tag = child.tag
            attr = self.mapping.get_attribute_by_repr(tag)
            if attr.kind != RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                value = self.__check_for_link(child)
            else:
                value = XmlConverterRegistry.convert_from_representation(
                                                            child.text,
                                                            attr.value_type)
            yield (tag, value)

    @property
    def data(self):
        data_map = OrderedDict()
        for (name, value) in self.iterator():
            data_map[name] = value
        return data_map

    def get_attribute(self, attr_name):
        attr = self.mapping.get_attribute_by_repr(attr_name)
        return self.__get_attribute(attr, False)

    def set_attribute(self, attr_name, value):
        attr = self.mapping.get_attribute_by_repr(attr_name)
        self.__set_attribute(attr, value)

    def __get_q_tag(self, attr):
        # FIXME: We should cache the namespace for each attribute.
        if not attr.namespace is None:
            q_tag = '{%s}%s' % (attr.namespace, attr.repr_name)
        else:
            if attr.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                xml_ns = \
                  self.mapping.configuration.get_option(XML_NAMESPACE_OPTION)
            else:
                if attr.kind == RESOURCE_ATTRIBUTE_KINDS.MEMBER:
                    attr_type = get_member_class(attr.value_type)
                elif attr.kind == RESOURCE_ATTRIBUTE_KINDS.COLLECTION:
                    attr_type = get_collection_class(attr.value_type)
                mp = self.mapping.mapping_registry.find_mapping(attr_type)
                if not mp is None:
                    xml_ns = mp.configuration.get_option(XML_NAMESPACE_OPTION)
                else: # pragma: no cover
                    # Not mapped.
                    # FIXME This case is neither tested nor documented.
                    xml_ns = None
            if not xml_ns is None:
                q_tag = '{%s}%s' % (xml_ns, attr.repr_name)
            else:
                q_tag = '{}%s' % attr.repr_name
        return q_tag

    def __get_attribute(self, attr, safe):
        if attr.repr_name == 'id':
            # The "special" id attribute.
            xml_val = self.get('id')
            if not xml_val is None:
                value = attr.value_type(xml_val)
            else:
                value = None
        else:
            q_tag = self.__get_q_tag(attr)
            child_it = self.iterchildren(q_tag)
            try:
                val_el = next(child_it)
            except StopIteration:
                if safe:
                    value = None
                else:
                    raise AttributeError(attr.repr_name)
            else:
                try:
                    next(child_it)
                except StopIteration:
                    pass
                else:
                    # This should never happen.
                    raise ValueError('More than one child for member '
                                     'attribute "%s" found.' % attr) # pragma: no cover
                if attr.kind != RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                    if val_el.text == self.__NONE_MARKER:
                        value = None
                    else:
                        value = self.__check_for_link(val_el)
                else:
                    value = XmlConverterRegistry.convert_from_representation(
                                                            val_el.text,
                                                            attr.value_type)
#            q_tag = self.__get_q_tag(attr)
#            val_el = getattr(self, q_tag, None)
#            if not val_el is None:
#                value = XmlConverterRegistry.convert_from_representation(
#                                                            val_el.text,
#                                                            attr.value_type)
#            else:
#                value = None
        return value

    def __set_attribute(self, attr, value):
        if attr.repr_name == 'id':
            # The "special" id attribute.
            self.set('id', str(value))
        else:
            q_tag = self.__get_q_tag(attr)
            if attr.kind != RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                if value is None:
                    setattr(self, q_tag, self.__NONE_MARKER)
                else:
                    if not isinstance(value, _XmlDataElementMixin):
                        raise ValueError('Non-terminal attribute value must '
                                         'be None or XML data element.')
                    value.tag = q_tag
                    self.append(value)
            else:
                xml_value = XmlConverterRegistry.convert_to_representation(
                                                            value,
                                                            attr.value_type)
                setattr(self, q_tag, xml_value)

    def __check_for_link(self, child):
        # Link handling: look for wrapper tag with *one* link child.
        if child.countchildren() == 1:
            grand_child = child.getchildren()[0]
            if ILinkedDataElement in provided_by(grand_child):
#                # We inject the id attribute from the wrapper element.
#                str_xml = child.get('id')
#                if not str_xml is None:
#                    grand_child.set('id', str_xml)
                child = grand_child
        return child


class XmlCollectionDataElement(objectify.ObjectifiedElement,
                               _XmlDataElementMixin, CollectionDataElement):
    def add_member(self, data_element):
        self.append(data_element)

    def get_members(self):
        return self.iterchildren()

    def __len__(self):
        return self.countchildren()


class XmlLinkedDataElement(objectify.ObjectifiedElement, LinkedDataElement):
    @classmethod
    def create(cls, url, kind,
               id=None, relation=None, title=None, **options): # pylint: disable=W0622
#        mp_reg = get_mapping_registry(XmlMime)
#        ns_map = mp_reg.namespace_map
        xml_ns = options[XML_NAMESPACE_OPTION]
        el_fac = XmlParserFactory.create().makeelement
        tag = '{%s}link' % xml_ns
        link_el = el_fac(tag)
        link_el.set('href', url)
        link_el.set('kind', kind)
        if not id is None:
            link_el.set('id', id)
        if not relation is None:
            link_el.set('rel', relation)
        if not title is None:
            link_el.set('title', title)
        return link_el

    @classmethod
    def create_from_resource(cls, resource):
        # Create the wrapping element.
        mp_reg = get_mapping_registry(XmlMime)
        mp = mp_reg.find_or_create_mapping(type(resource))
        xml_ns = mp.configuration.get_option(XML_NAMESPACE_OPTION)
        options = {XML_NAMESPACE_OPTION:xml_ns}
        rc_data_el = mp.create_data_element_from_resource(resource)
        if provides_member_resource(resource):
            link_el = cls.create(resource_to_url(resource),
                                 RESOURCE_KINDS.MEMBER,
                                 id=str(resource.id),
                                 relation=resource.relation,
                                 title=resource.title,
                                 **options)
            rc_data_el.set('id', str(resource.id))
            rc_data_el.append(link_el)
        else: # collection resource.
            # Collection links only get an actual link element if they
            # contain any members.
            link_el = cls.create(resource_to_url(resource),
                                 RESOURCE_KINDS.COLLECTION,
                                 relation=resource.relation,
                                 title=resource.title,
                                 **options)
            rc_data_el.append(link_el)
        return rc_data_el

    def get_url(self):
        return self.get('href')

    def get_kind(self):
        return self.get('kind')

    def get_relation(self):
        return self.get('rel')

    def get_title(self):
        return self.get('title')

    def get_id(self):
        # FIXME: This will not work with ID strings that happen to be
        #        convertible to an int.
        id_str = self.get('id')
        try:
            id_val = int(id_str)
        except ValueError:
            id_val = id_str
        except TypeError: # Happens if the id string is None.
            id_val = id_str
        return id_val


class XmlRepresenterConfiguration(RepresenterConfiguration):
    """
    Specialized configuration class for XML representers.

    Allowed configuration attribute names:

    xml_tag :
        The XML tag to use for the represented data element class.
    xml_schema :
        The XML schema to use for the represented data element class.
    xml_ns :
        The XML namespace to use for the represented data element class.
    xml_prefix :
        The XML namespace prefix to use for the represented data element
        class.
    xml_validate:
        Boolean flag indicating if incoming representations should be
        validated upon parsing (defaults to `True`).
    """
    _default_config_options = \
        dict(list(RepresenterConfiguration._default_config_options.items())
             + [(XML_TAG_OPTION, None), (XML_SCHEMA_OPTION, None),
                (XML_NAMESPACE_OPTION, None), (XML_PREFIX_OPTION, None),
                (XML_VALIDATE_OPTION, True)])
    _default_attributes_options = \
        dict(list(RepresenterConfiguration._default_attributes_options.items())
             + [(NAMESPACE_MAPPING_OPTION, None)])


class XmlMappingRegistry(MappingRegistry):
    """
    Registry for XML mappings.
    """

    member_data_element_base_class = XmlMemberDataElement
    collection_data_element_base_class = XmlCollectionDataElement
    linked_data_element_base_class = XmlLinkedDataElement
    configuration_class = XmlRepresenterConfiguration

    #: Static namespace prefix: namespace map.
    NS_MAP = dict(xsi=XML_NS_XSI)

    def __init__(self):
        MappingRegistry.__init__(self)
        self.__ns_map = self.__class__.NS_MAP.copy()
        self.__ns_lookup = None

    def _initialize(self):
        # Create and register the linked data element class.
        configuration = self.configuration_class()
        mapping = self.create_mapping(Link, configuration)
        self.set_mapping(mapping)

    def set_mapping(self, mapping):
        # First, record the namespace and prefix, if necessary.
        xml_ns = mapping.configuration.get_option(XML_NAMESPACE_OPTION)
        if not xml_ns is None:
            xml_prefix = mapping.configuration.get_option(XML_PREFIX_OPTION)
            if not xml_prefix is None:
                ns = self.__ns_map.get(xml_prefix)
                if ns is None:
                    # New prefix - register.
                    self.__ns_map[xml_prefix] = xml_ns
                elif xml_ns != ns:
                    raise ValueError('Prefix "%s" is already registered for '
                                     'namespace %s.' % (xml_prefix, ns))
        # Make sure we rebuild the lookup.
        if not self.__ns_lookup is None:
            self.__ns_lookup = None
        MappingRegistry.set_mapping(self, mapping)

    @property
    def namespace_map(self):
        return self.__ns_map.copy()

    @property
    def parsing_lookup(self):
        if self.__ns_lookup is None:
            self.__ns_lookup = self.__create_parsing_lookup()
        return self.__ns_lookup

    def __create_parsing_lookup(self):
        lookup = etree.ElementNamespaceClassLookup(
                                objectify.ObjectifyElementClassLookup())
        for mapping in self.get_mappings():
            de_cls = mapping.data_element_class
            if issubclass(de_cls, XmlLinkedDataElement):
                continue
            xml_ns = mapping.configuration.get_option(XML_NAMESPACE_OPTION)
            xml_tag = bytes_(mapping.configuration.get_option(XML_TAG_OPTION))
            ns_cls_map = lookup.get_namespace(xml_ns)
            if xml_tag in ns_cls_map:
                raise ValueError('Duplicate tag "%s" in namespace "%s" '
                                 '(trying to register class %s)'
                                 % (xml_tag, xml_ns, de_cls))
            ns_cls_map[xml_tag] = de_cls
            ns_cls_map['link'] = XmlLinkedDataElement
        return lookup
