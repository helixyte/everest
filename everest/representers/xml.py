"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

XML representers.

Created on May 19, 2011.
"""
from everest.mime import XmlMime
from everest.representers.base import RepresentationGenerator
from everest.representers.base import RepresentationParser
from everest.representers.base import ResourceRepresenter
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
from everest.resources.attributes import ResourceAttributeKinds
from everest.resources.kinds import ResourceKinds
from everest.resources.link import Link
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_member_class
from everest.resources.utils import provides_member_resource
from everest.url import resource_to_url
from lxml import etree
from lxml import objectify
from pkg_resources import resource_filename # pylint: disable=E0611
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
import datetime

__docformat__ = 'reStructuredText en'
__all__ = ['XmlDataElement',
           'XmlDataElementRegistry',
           'XmlLinkedDataElement',
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
        except etree.XMLSyntaxError, err:
            raise SyntaxError('Could not parse XML document for schema %s.'
                              '\n%s' % (schema_loc, err.msg))
        return tree.getroot()[0]


class XmlRepresentationGenerator(RepresentationGenerator):
    def run(self, data_element):
        objectify.deannotate(data_element)
        etree.cleanup_namespaces(data_element)
        encoding = self.get_option('encoding')
        self._stream.write(etree.tostring(data_element,
                                          pretty_print=True,
                                          encoding=encoding,
                                          xml_declaration=True))


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
        except etree.XMLSyntaxError, err:
            raise SyntaxError('Could not parse XML schema %s.\n%s' %
                              (xml_schema_path, err.msg))
        try:
            schema = etree.XMLSchema(doc)
        except etree.XMLSchemaParseError, err:
            raise SyntaxError('Invalid XML schema.\n Parser message: %s'
                              % err.message)
        return schema


class XmlResourceRepresenter(ResourceRepresenter):

    content_type = XmlMime

    #: The encoding to use for reading and writing XML.
    ENCODING = 'utf-8'

    @classmethod
    def make_mapping_registry(cls):
        return XmlMappingRegistry()

    def _make_representation_parser(self, stream, resource_class, mapping):
        parser = XmlRepresentationParser(stream, resource_class, mapping)
        mp = self._mapping
        xml_schema = mp.configuration.get_option(XML_SCHEMA_OPTION)
        parser.set_option('schema_location', xml_schema)
        return parser

    def _make_representation_generator(self, stream, resource_class, mapping):
        generator = XmlRepresentationGenerator(stream, resource_class, mapping)
        generator.set_option('encoding', self.ENCODING)
        return generator


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

    def get_mapped_nested(self, attr):
        # We only allow *one* child with the given name.
        q_tag = self.__get_q_tag(attr)
        child_it = self.iterchildren(q_tag)
        try:
            child = child_it.next()
        except StopIteration:
            child = None
        else:
            try:
                child_it.next()
            except StopIteration:
                pass
            else:
                # This should never happen.
                raise ValueError('More than one child for member '
                                 'attribute "%s" found.' % attr) # pragma: no cover
            # Link handling: look for wrapper tag with *one* link child.
            if child.countchildren() == 1:
                grand_child = child.getchildren()[0]
                if ILinkedDataElement in provided_by(grand_child):
                    # We inject the id attribute from the wrapper element.
                    str_xml = child.get('id')
                    if not str_xml is None:
                        grand_child.set('id', str_xml)
                    child = grand_child
        return child

    def set_mapped_nested(self, attr, data_element):
        data_element.tag = self.__get_q_tag(attr)
        self.append(data_element)

    def get_mapped_terminal(self, attr):
        if attr.repr_name == 'id':
            # The "special" id attribute.
            xml_val = self.get('id')
            if not xml_val is None:
                val = attr.value_type(xml_val)
            else:
                val = None
        else:
            q_tag = self.__get_q_tag(attr)
            val_el = getattr(self, q_tag, None)
            if not val_el is None:
                val = XmlConverterRegistry.convert_from_representation(
                                                            val_el.text,
                                                            attr.value_type)
            else:
                val = None
        return val

    def set_mapped_terminal(self, attr, value):
        if attr.repr_name == 'id':
            # The "special" id attribute.
            self.set('id', str(value))
        else:
            q_tag = self.__get_q_tag(attr)
            xml_value = XmlConverterRegistry.convert_to_representation(
                                                            value,
                                                            attr.value_type)
            setattr(self, q_tag, xml_value)

    @property
    def data(self):
        data_map = {}
        for child in self.iterchildren():
            idx = child.tag.find('}')
            if idx != -1:
                tag = child.tag[idx + 1:]
            else:
                tag = child.tag
            data_map[tag] = child.text
        return data_map

    def __get_q_tag(self, attr):
        if not attr.namespace is None:
            q_tag = '{%s}%s' % (attr.namespace, attr.repr_name)
        else:
            if attr.kind == ResourceAttributeKinds.TERMINAL:
                xml_ns = \
                  self.mapping.configuration.get_option(XML_NAMESPACE_OPTION)
            else:
                if attr.kind == ResourceAttributeKinds.MEMBER:
                    attr_type = get_member_class(attr.value_type)
                elif attr.kind == ResourceAttributeKinds.COLLECTION:
                    attr_type = get_collection_class(attr.value_type)
                mp = self.mapping.mapping_registry.find_mapping(attr_type)
                xml_ns = mp.configuration.get_option(XML_NAMESPACE_OPTION)
            if not xml_ns is None:
                q_tag = '{%s}%s' % (xml_ns, attr.repr_name)
            else:
                q_tag = attr.repr_name
        return q_tag


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
    def create(cls, url, kind, relation=None, title=None, **options):
#        mp_reg = get_mapping_registry(XmlMime)
#        ns_map = mp_reg.namespace_map
        xml_ns = options[XML_NAMESPACE_OPTION]
        el_fac = XmlParserFactory.create().makeelement
        tag = '{%s}link' % xml_ns
        link_el = el_fac(tag)
        link_el.set('href', url)
        link_el.set('kind', kind)
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
                                 ResourceKinds.MEMBER,
                                 relation=resource.relation,
                                 title=resource.title,
                                 **options)
            rc_data_el.set('id', str(resource.id))
            rc_data_el.append(link_el)
        else: # collection resource.
            # Collection links only get an actual link element if they
            # contain any members.
            link_el = cls.create(resource_to_url(resource),
                                 ResourceKinds.COLLECTION,
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
        return self.get('id')


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
        The XML namespace prefix to use for the represented data element class.
    """
    _default_config_options = \
            dict(RepresenterConfiguration._default_config_options.items()
                 + [(XML_TAG_OPTION, None), (XML_SCHEMA_OPTION, None),
                    (XML_NAMESPACE_OPTION, None), (XML_PREFIX_OPTION, None)])
    _default_attributes_options = \
            dict(RepresenterConfiguration._default_attributes_options.items()
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
            xml_tag = mapping.configuration.get_option(XML_TAG_OPTION)
            ns_cls_map = lookup.get_namespace(xml_ns)
            if xml_tag in ns_cls_map:
                raise ValueError('Duplicate tag "%s" in namespace "%s" '
                                 '(trying to register class %s)'
                                 % (xml_tag, xml_ns, de_cls))
            ns_cls_map[xml_tag] = de_cls
            ns_cls_map['link'] = XmlLinkedDataElement
        return lookup
