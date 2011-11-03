"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

XML representers.

Created on May 19, 2011.
"""

from everest.mime import XmlMime
from everest.representers.base import DataElement
from everest.representers.base import DataElementGenerator
from everest.representers.base import DataElementParser
from everest.representers.base import DataElementRegistry
from everest.representers.base import LinkedDataElement
from everest.representers.base import RepresentationGenerator
from everest.representers.base import RepresentationParser
from everest.representers.base import RepresenterConfiguration
from everest.representers.base import ResourceRepresenter
from everest.representers.interfaces import ILinkedDataElement
from everest.representers.utils import get_data_element_registry
from everest.resources.base import Link
from everest.resources.interfaces import IMemberResource
from everest.url import resource_to_url
from lxml import etree
from lxml import objectify
from pkg_resources import resource_filename # pylint: disable=E0611
from rfc3339 import rfc3339
from zope.interface import Interface # pylint: disable=E0611,F0401
from zope.interface import implements # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
import iso8601

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
XML_NS_SHARED = 'http://schemata.cenix-bioscience.com/shared'
XML_NS_XSI = 'http://www.w3.org/2001/XMLSchema-instance'

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


class NoOpConverter(object):

    implements(IConverter)

    @classmethod
    def from_xml(cls, value):
        return value

    @classmethod
    def to_xml(cls, value):
        return value


class DateTimeConverter(object):
    implements(IConverter)

    @classmethod
    def from_xml(cls, value):
        return iso8601.parse_date(value)

    @classmethod
    def to_xml(cls, value):
        return rfc3339(value)


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
            de_reg = get_data_element_registry(XmlMime)
            cls.__parser = cls.create(de_reg.get_parsing_lookup())
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
    def make_data_element_registry(cls):
        return XmlDataElementRegistry()

    def _make_representation_parser(self, stream, resource_class, **config):
        parser = XmlRepresentationParser(stream, resource_class)
        de_reg = self._data_element_registry
        de_cls = de_reg.get_data_element_class(resource_class)
        xml_schema = de_cls.mapper.get_config_option('xml_schema')
        parser.set_option('schema_location', xml_schema)
        parser.set_option('class_lookup', de_reg.get_parsing_lookup())
        parser.configure(**config)
        return parser

    def _make_representation_generator(self, stream, resource_class, **config):
        generator = XmlRepresentationGenerator(stream, resource_class)
        generator.set_option('encoding', self.ENCODING)
        generator.configure(**config)
        return generator

    def _make_data_element_parser(self):
        return DataElementParser()

    def _make_data_element_generator(self):
        return DataElementGenerator(self._data_element_registry)


# Adapter creating representers from resource instances.
resource_adapter = XmlResourceRepresenter.create_from_resource


class XmlDataElement(objectify.ObjectifiedElement, DataElement):

    # XML schema definitions: schema location, namespace, tag, prefix.
    # These attributes are set when new data element classes are registered.

    @classmethod
    def create(cls):
        el_fac = XmlParserFactory.get_default().makeelement
        return el_fac()

    @classmethod
    def create_from_resource(cls, resource, ns_map=None): # ignore resource pylint:disable=W0613,W0221
        if ns_map is None:
            de_reg = get_data_element_registry(XmlMime)
            ns_map = de_reg.get_namespace_map()
        cls_xml_ns = cls.mapper.get_config_option('xml_ns')
        cls_xml_tag = cls.mapper.get_config_option('xml_tag')
        ns_map[None] = cls_xml_ns
        el_fac = XmlParserFactory.get_default().makeelement
        tag = "{%s}%s" % (cls_xml_ns, cls_xml_tag)
        return el_fac(tag, nsmap=ns_map)

    def get_nested(self, attr):
        # We only allow *one* child with the given name.
        if not attr.namespace is None:
            q_tag = '{%s}%s' % (attr.namespace, attr.representation_name)
        else:
            xml_ns = self.mapper.get_config_option('xml_ns')
            q_tag = '{%s}%s' % (xml_ns, attr.representation_name)
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
            custom_tag = '{%s}%s' % (attr.namespace, attr.representation_name)
#            if hasattr(self, custom_tag):
#                raise ValueError('Data element has already a child for member '
#                                 'attribute "%s".' % attr)
            data_element.tag = custom_tag
        self.append(data_element)

#        if isinstance(data_element, XmlLinkedDataElement):
#            # Link handling: create wrapper tag.
#            if needs_custom_tag:
#                wrapper_el = etree.SubElement(self, custom_tag)
#            else:
#                ns = data_element.nsmap[data_element.prefix]
#                wrapper_el = \
#                    etree.SubElement(self,
#                                     '{%s}%s' % (ns, attr.representation_name))
#            wrapper_el.append(data_element)
#            # Process ID. Only the wrapper element *must* have the id
#            # attribute set.
#            id_str = data_element.get('id')
#            if not id_str is None:
#                wrapper_el.set('id', id_str)
#                del data_element.attrib['id']

    def add_member(self, data_element):
        self.append(data_element)

    def get_members(self):
        return self.iterchildren()

    def get_terminal(self, attr):
        if attr.representation_name == 'id':
            # The "special" id attribute.
            xml_val = self.get('id')
            if not xml_val is None:
                val = attr.value_type(xml_val)
            else:
                val = None
        else:
            xml_ns = self.mapper.get_config_option('xml_ns')
            q_tag = '{%s}%s' % (xml_ns, attr.representation_name)
            val_el = getattr(self, q_tag, None)
            if not val_el is None:
                if attr.converter is None:
                    val = val_el.pyval
                else:
                    val = attr.converter.from_xml(val_el.text)
            else:
                val = None
        return val

    def set_terminal(self, attr, value):
        if attr.representation_name == 'id':
            # The "special" id attribute.
            self.set('id', str(value))
        else:
            xml_ns = self.mapper.get_config_option('xml_ns')
            q_tag = '{%s}%s' % (xml_ns, attr.representation_name)
            if not attr.converter is None:
                value = attr.converter.to_xml(value)
            setattr(self, q_tag, value)


class XmlLinkedDataElement(objectify.ObjectifiedElement, LinkedDataElement):

    @classmethod
    def create(cls, linked_data_element_class, url,
               relation=None, title=None):
#        de_reg = get_data_element_registry(XmlMime)
#        ns_map = de_reg.get_namespace_map()
        el_fac = XmlParserFactory.get_default().makeelement
        xml_ns = linked_data_element_class.mapper.get_config_option('xml_ns')
        tag = '{%s}link' % xml_ns
        link_el = el_fac(tag)
        link_el.set('href', url)
        if not relation is None:
            link_el.set('rel', relation)
        if not title is None:
            link_el.set('title', title)
        return link_el

    @classmethod
    def create_from_resource(cls, resource):
        # Create the wrapping element.
        de_reg = get_data_element_registry(XmlMime)
        rc_de_cls = de_reg.get_data_element_class(type(resource))
        rc_data_el = rc_de_cls.create_from_resource(resource)
#        rc_data_el = objectify.ObjectifiedElement()
#        cls_xml_ns = rc_de_cls.mapper.get_config_option('xml_ns')
#        cls_xml_tag = rc_de_cls.mapper.get_config_option('xml_tag')
#        rc_data_el.tag = '{%s}%s' % (cls_xml_ns, cls_xml_tag)
        if IMemberResource in provided_by(resource):
            link_el = cls.create(rc_de_cls, resource_to_url(resource),
                                 relation=resource.relation,
                                 title=resource.title)
            rc_data_el.set('id', str(resource.id))
            rc_data_el.append(link_el)
        elif len(resource) > 0:
            # Collection links only get an actual link element if they
            # contain any members.
            link_el = cls.create(rc_de_cls, resource_to_url(resource),
                                 relation=resource.relation,
                                 title=resource.title)
            rc_data_el.append(link_el)
        return rc_data_el

    def get_url(self):
        return self.get('href')

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
    _config_attributes = RepresenterConfiguration._config_attributes + \
                         ['xml_tag', 'xml_schema', 'xml_ns', 'xml_prefix']
    _mapping_options = RepresenterConfiguration._mapping_options + \
                       ['converter', 'namespace']


class XmlDataElementRegistry(DataElementRegistry):
    """
    Registry for XML data element classes.
    """

    data_element_class = XmlDataElement
    linked_data_element_class = XmlLinkedDataElement
    configuration_class = XmlRepresenterConfiguration

    #: Static namespace prefix: namespace map.
    #FIXME move the opensearch ns to atom pylint:disable=W0511
    NS_MAP = dict(xsi=XML_NS_XSI,
                  opensearch=XML_NS_OPEN_SEARCH)

    __ns_map = None

    def _initialize(self):
        # Create and register the linked data element class.
        configuration = XmlRepresenterConfiguration(
                            dict(xml_prefix='sh',
                                 xml_ns=XML_NS_SHARED,
                                 xml_schema='everest:schemata/Shared.xsd'))
        de_cls = \
            self.create_data_element_class(Link, configuration,
                                           base_class=XmlLinkedDataElement)
        self.set_data_element_class(de_cls)

    def set_data_element_class(self, data_element_class):
        # First, try to record the prefix.
        ns_map = self.get_namespace_map()
        xml_prefix = data_element_class.mapper.get_config_option('xml_prefix')
        xml_ns = data_element_class.mapper.get_config_option('xml_ns')
        ns = ns_map.get(xml_prefix)
        if ns is None:
            # New prefix - register.
            ns_map[xml_prefix] = xml_ns
        elif xml_ns != ns:
            raise ValueError('Prefix "%s" is already registered for namespace '
                             '%s.' % (xml_prefix, ns))
        DataElementRegistry.set_data_element_class(self, data_element_class)

    def get_namespace_map(self):
        if self.__ns_map is None:
            self.__ns_map = self.NS_MAP.copy()
        return self.__ns_map

    def get_parsing_lookup(self):
        lookup = etree.ElementNamespaceClassLookup(
                                objectify.ObjectifyElementClassLookup())
        for reg_item in self.get_data_element_classes():
            de_cls = reg_item[1]
            if issubclass(de_cls, XmlLinkedDataElement):
                continue
            xml_ns = de_cls.mapper.get_config_option('xml_ns')
            xml_tag = de_cls.mapper.get_config_option('xml_tag')
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
