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
from everest.representers.dataelements import CollectionDataElement
from everest.representers.dataelements import LinkedDataElement
from everest.representers.dataelements import MemberDataElement
from everest.representers.interfaces import ILinkedDataElement
from everest.representers.mapping import MappingRegistry
from everest.representers.utils import get_mapping_registry
from everest.resources.kinds import ResourceKinds
from everest.resources.link import Link
from everest.resources.utils import provides_collection_resource
from everest.resources.utils import provides_member_resource
from everest.url import resource_to_url
from lxml import etree
from lxml import objectify
from pkg_resources import resource_filename # pylint: disable=E0611
from rfc3339 import rfc3339
from zope.interface import Interface # pylint: disable=E0611,F0401
from zope.interface import implements # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
import iso8601
import datetime

__docformat__ = 'reStructuredText en'
__all__ = ['DateTimeConverter',
           'IConverter',
           'NoOpConverter',
           'XmlDataElement',
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


# begin interface pylint:disable=W0232, E0213
class IConverter(Interface):
    def from_xml(value):
        """
        Converts the given XML string to a Python value object.
        """

    def to_xml(value):
        """
        Converts the given Python value object into an XML string.
        """
# end interface pylint:enable=W0232, E0213


class XmlConverterRegistry(object):
    __converters = {}

    @classmethod
    def register(cls, value_type, converter_class):
        if value_type in cls.__converters:
            raise ValueError('For the "%s" XML data type, a converter has '
                             'already been registered (%s).'
                             % (value_type, cls.__converters[value_type]))
        cls.__converters[value_type] = converter_class

    @classmethod
    def convert_from_xml(cls, xml_value, value_type):
        cnv = cls.__converters.get(value_type)
        if not cnv is None:
            value = cnv.from_xml(xml_value)
        else:
            # Try the value type's constructor.
            value = value_type(xml_value)
        return value

    @classmethod
    def convert_to_xml(cls, value, value_type):
        cnv = cls.__converters.get(value_type)
        if not cnv is None:
            xml_value = cnv.to_xml(value)
        else:
            xml_value = str(value) # FIXME: use unicode?
        return xml_value


class DateTimeConverter(object):
    implements(IConverter)

    @classmethod
    def from_xml(cls, value):
        return iso8601.parse_date(value)

    @classmethod
    def to_xml(cls, value):
        return rfc3339(value)


XmlConverterRegistry.register(datetime.datetime, DateTimeConverter)


class XmlRepresentationParser(RepresentationParser):

    def run(self):
        # Create an XML schema.
        schema_loc = self.get_option('schema_location')
        class_lookup = self.get_option('class_lookup')
        parser = XmlParserFactory.create(class_lookup,
                                         schema_location=schema_loc)
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
    def create(cls, class_lookup, schema_location=None):
        if not schema_location is None:
            schema = cls.__get_xml_schema(schema_location)
            parser = objectify.makeparser(schema=schema)
        else:
            parser = objectify.makeparser()
        parser.set_element_class_lookup(class_lookup)
        return parser

    @classmethod
    def get_default(cls):
        if cls.__parser is None:
            mp_reg = get_mapping_registry(XmlMime)
            cls.__parser = cls.create(mp_reg.get_parsing_lookup())
        return cls.__parser

    @classmethod
    def __get_xml_schema(cls, xml_schema_path):
        try:
            doc = etree.parse(resource_filename(*xml_schema_path.split(':')))
        except etree.XMLSyntaxError, err:
            raise SyntaxError('Could not parse %s.\n%s' %
                              (xml_schema_path, err.msg))
        return etree.XMLSchema(doc)


class XmlResourceRepresenter(ResourceRepresenter):

    content_type = XmlMime

    #: The encoding to use for reading and writing XML.
    ENCODING = 'utf-8'

    @classmethod
    def make_mapping_registry(cls):
        return XmlMappingRegistry()

    def _make_representation_parser(self, stream, resource_class, **config):
        parser = XmlRepresentationParser(stream, resource_class)
        mp = self._mapping_registry.find_or_create_mapping(resource_class)
        xml_schema = mp.get_config_option(XML_SCHEMA_OPTION)
        parser.set_option('schema_location', xml_schema)
        parser.set_option('class_lookup',
                          self._mapping_registry.get_parsing_lookup())
        parser.configure(**config)
        return parser

    def _make_representation_generator(self, stream, resource_class, **config):
        generator = XmlRepresentationGenerator(stream, resource_class)
        generator.set_option('encoding', self.ENCODING)
        generator.configure(**config)
        return generator


class _XmlDataElementMixin(object):
    @classmethod
    def create(cls):
        el_fac = XmlParserFactory.get_default().makeelement
        return el_fac()

    @classmethod
    def create_from_resource(cls, resource, ns_map=None): # ignore resource pylint:disable=W0613,W0221
        if ns_map is None:
            mp_reg = get_mapping_registry(XmlMime)
            ns_map = mp_reg.get_namespace_map()
        cls_xml_ns = cls.mapping.get_config_option(XML_NAMESPACE_OPTION)
        cls_xml_tag = cls.mapping.get_config_option(XML_TAG_OPTION)
        ns_map[None] = cls_xml_ns
        el_fac = XmlParserFactory.get_default().makeelement
        tag = "{%s}%s" % (cls_xml_ns, cls_xml_tag)
        return el_fac(tag, nsmap=ns_map)


class XmlMemberDataElement(objectify.ObjectifiedElement,
                           _XmlDataElementMixin, MemberDataElement):

    def get_nested(self, attr):
        # We only allow *one* child with the given name.
        if not attr.namespace is None:
            q_tag = '{%s}%s' % (attr.namespace, attr.repr_name)
        else:
            xml_ns = self.mapping.get_config_option(XML_NAMESPACE_OPTION)
            q_tag = '{%s}%s' % (xml_ns, attr.repr_name)
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
                raise ValueError('More than one child for member attribute '
                                 '"%s" found.' % attr)
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

    def set_nested(self, attr, data_element):
        needs_custom_tag = not attr.namespace is None
        if needs_custom_tag:
            custom_tag = '{%s}%s' % (attr.namespace, attr.repr_name)
            data_element.tag = custom_tag
        self.append(data_element)

    def get_terminal(self, attr):
        if attr.repr_name == 'id':
            # The "special" id attribute.
            xml_val = self.get('id')
            if not xml_val is None:
                val = attr.value_type(xml_val)
            else:
                val = None
        else:
            xml_ns = self.mapping.get_config_option(XML_NAMESPACE_OPTION)
            q_tag = '{%s}%s' % (xml_ns, attr.repr_name)
            val_el = getattr(self, q_tag, None)
            if not val_el is None:
                val = XmlConverterRegistry.convert_from_xml(val_el.text,
                                                            attr.value_type)
            else:
                val = None
        return val

    def set_terminal(self, attr, value):
        if attr.repr_name == 'id':
            # The "special" id attribute.
            self.set('id', str(value))
        else:
            xml_ns = self.mapping.get_config_option(XML_NAMESPACE_OPTION)
            q_tag = '{%s}%s' % (xml_ns, attr.repr_name)
            xml_value = XmlConverterRegistry.convert_to_xml(value,
                                                            attr.value_type)
            setattr(self, q_tag, xml_value)


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
#        ns_map = mp_reg.get_namespace_map()
        xml_ns = options[XML_NAMESPACE_OPTION]
        el_fac = XmlParserFactory.get_default().makeelement
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
        options = \
            {XML_NAMESPACE_OPTION:mp.get_config_option(XML_NAMESPACE_OPTION)}
        rc_data_el = mp.create_data_element_from_resource(resource)
        if provides_member_resource(resource):
            link_el = cls.create(resource_to_url(resource),
                                 ResourceKinds.MEMBER,
                                 relation=resource.relation,
                                 title=resource.title,
                                 **options)
            rc_data_el.set('id', str(resource.id))
            rc_data_el.append(link_el)
        elif provides_collection_resource(resource):
            # Collection links only get an actual link element if they
            # contain any members.
            link_el = cls.create(resource_to_url(resource),
                                 ResourceKinds.COLLECTION,
                                 relation=resource.relation,
                                 title=resource.title,
                                 **options)
            rc_data_el.append(link_el)
        else:
            raise ValueError('"%s" is not a resource.' % resource)
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
            dict(RepresenterConfiguration._default_config_options.items() +
                 [(XML_TAG_OPTION, None),
                  (XML_SCHEMA_OPTION, None),
                  (XML_NAMESPACE_OPTION, None),
                  (XML_PREFIX_OPTION, None)])
    _default_mapping_options = \
            dict(RepresenterConfiguration._default_mapping_options.items() +
                 [(NAMESPACE_MAPPING_OPTION, None)])


class XmlMappingRegistry(MappingRegistry):
    """
    Registry for XML mappings.
    """

    member_data_element_base_class = XmlMemberDataElement
    collection_data_element_base_class = XmlCollectionDataElement
    linked_data_element_base_class = XmlLinkedDataElement
    configuration_class = XmlRepresenterConfiguration

    #: Static namespace prefix: namespace map.
    # FIXME: move the opensearch ns to atom.
    NS_MAP = dict(xsi=XML_NS_XSI,
                  opensearch=XML_NS_OPEN_SEARCH)

    __ns_map = None

    def _initialize(self):
        # Create and register the linked data element class.
        configuration = self.configuration_class()
        mapping = self.create_mapping(Link, configuration)
        self.set_mapping(mapping)

    def set_mapping(self, mapping):
        # First, try to record the prefix.
        ns_map = self.get_namespace_map()
        xml_prefix = mapping.get_config_option(XML_PREFIX_OPTION)
        xml_ns = mapping.get_config_option(XML_NAMESPACE_OPTION)
        ns = ns_map.get(xml_prefix)
        if ns is None:
            # New prefix - register.
            ns_map[xml_prefix] = xml_ns
        elif xml_ns != ns:
            raise ValueError('Prefix "%s" is already registered for namespace '
                             '%s.' % (xml_prefix, ns))
        MappingRegistry.set_mapping(self, mapping)

    def get_namespace_map(self):
        if self.__ns_map is None:
            self.__ns_map = self.NS_MAP.copy()
        return self.__ns_map

    def get_parsing_lookup(self):
        lookup = etree.ElementNamespaceClassLookup(
                                objectify.ObjectifyElementClassLookup())
        for reg_item in self.get_mappings():
            de_cls = reg_item[1].data_element_class
            if issubclass(de_cls, XmlLinkedDataElement):
                continue
            xml_ns = de_cls.mapping.get_config_option(XML_NAMESPACE_OPTION)
            xml_tag = de_cls.mapping.get_config_option(XML_TAG_OPTION)
            ns_cls_map = lookup.get_namespace(xml_ns)
            if xml_tag in ns_cls_map:
                raise ValueError('Duplicate tag "%s" in namespace "%s" '
                                 '(trying to register class %s)'
                                 % (xml_tag, xml_ns, de_cls))
            ns_cls_map[xml_tag] = de_cls
        for ns in self.get_namespace_map().values():
            ns_cls_map = lookup.get_namespace(ns)
            ns_cls_map['link'] = XmlLinkedDataElement
        return lookup
