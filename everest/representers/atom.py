"""
ATOM representers.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 19, 2011.
"""
from everest.mime import AtomMime
from everest.mime import XmlMime
from everest.representers.base import MappingResourceRepresenter
from everest.representers.mapping import Mapping
from everest.representers.utils import get_mapping_registry
from everest.representers.xml import XmlMappingRegistry
from everest.representers.xml import XmlRepresentationGenerator
from everest.representers.xml import XmlRepresenterConfiguration
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.utils import provides_member_resource
from everest.url import UrlPartsConverter

__docformat__ = 'reStructuredText en'
__all__ = ['AtomMapping',
           'AtomMappingRegistry',
           'AtomRepresenterConfiguration',
           'AtomResourceRepresenter',
           ]

XML_NS_OPEN_SEARCH = 'http://a9.com/-/spec/opensearch/1.1/'
XML_NS_ATOM = 'http://www.w3.org/2005/Atom'
XML_PREFIX_OPEN_SEARCH = 'opensearch'
XML_PREFIX_ATOM = 'atom'


class AtomResourceRepresenter(MappingResourceRepresenter):
    """
    Resource representer implementation for ATOM.
    """
    content_type = AtomMime

    def from_stream(self, stream, resource=None):
        # We do not support parsing ATOM representations.
        raise NotImplementedError('Not implemented.')

    def parse(self, parser):
        # We do not support parsing ATOM representations.
        raise NotImplementedError('Not implemented.')

    @classmethod
    def make_mapping_registry(cls):
        return AtomMappingRegistry()

    def _make_representation_parser(self, stream, resource_class, mapping):
        # We do not support parsing ATOM representations.
        raise NotImplementedError('Not implemented.')

    def _make_representation_generator(self, stream, resource_class, mapping):
        return XmlRepresentationGenerator(stream, resource_class, mapping)


class AtomMapping(Mapping):
    # FIXME: Make the hypermedia type configurable. pylint: disable=W0511
    VND_MIME = 'application/vnd.everest+xml'

    def map_to_data_element(self, resource):
        # We use the XML mapping for the content serialization.
        xml_mp_reg = get_mapping_registry(XmlMime)
        xml_mp = xml_mp_reg.find_or_create_mapping(type(resource))
        ns_map = self.mapping_registry.namespace_map
        atom_mp = self.mapping_registry.find_or_create_mapping(type(resource))
        data_el = \
            atom_mp.data_element_class.create_from_resource(resource,
                                                            ns_map=ns_map)
        if provides_member_resource(resource):
            self.__map_member_to_data_element(data_el, resource, xml_mp)
        else:
            self.__map_collection_to_data_element(data_el, resource, xml_mp)
        return data_el

    def __map_member_to_data_element(self, data_el, member, xml_mp):
        # Fill in ATOM tags.
        # FIXME: Should not use etree API here pylint: disable=W0511
        data_el.title = member.title
        data_el.id = member.urn
        self.__append_links(data_el, member.links)
        # FIXME: Make the media type configurable. pylint: disable=W0511
        type_string = '%s;type=%s' % (self.VND_MIME, member.__class__.__name__)
        cnt_wrapper_el = data_el.makeelement('content',
                                             type=type_string)
        # Create content.
        content_data_el = xml_mp.map_to_data_element(member)
        cnt_wrapper_el.append(content_data_el)
        data_el.append(cnt_wrapper_el)

    def __map_collection_to_data_element(self, data_el, collection, xml_mp):
        # Fill in ATOM tags.
        # FIXME: Should not use etree API here pylint: disable=W0511
        data_el.title = collection.title
        data_el.subtitle = collection.description
        data_el.generator = collection.title
        data_el.generator.set('uri', collection.path)
        data_el.id = collection.urn
        # FIXME: Make the media type configurable. pylint: disable=W0511
        type_string = '%s;type=%s' % (self.VND_MIME,
                                      collection.__class__.__name__)
        cnt_type_el = data_el.makeelement('content_type',
                                          name=type_string)
        data_el.append(cnt_type_el)
        #
        self.__append_opensearch_elements(data_el, collection)
        self.__append_links(data_el, collection.links)
        # Iterate over members and serialize as ATOM entries.
        for member in collection:
            member_data_el = self.create_data_element_from_resource(member)
            self.__map_member_to_data_element(member_data_el, member, xml_mp)
            data_el.append(member_data_el)

    def __append_links(self, resource_data_el, links):
        for link in links:
            attr_map = {}
            for attr in ['rel', 'href', 'title', 'type', 'length']:
                value = getattr(link, attr)
                if value is None:
                    continue
                attr_map[attr] = value
            link_el = resource_data_el.makeelement('link', attrib=attr_map)
            resource_data_el.append(link_el)

    def __append_opensearch_elements(self, coll_data_el, collection):
        if collection.filter:
            search_terms = \
                    UrlPartsConverter.make_filter_string(collection.filter)
        else:
            search_terms = ''
        if collection.order:
            sort_terms = UrlPartsConverter.make_order_string(collection.order)
        else:
            sort_terms = UrlPartsConverter.make_order_string(
                                                    collection.default_order)
        # Query.
        q_tag = '{%s}%s' % (XML_NS_OPEN_SEARCH, 'Query')
        q_el = coll_data_el.makeelement(
                                q_tag,
                                attrib=dict(role='request',
                                            searchTerms=search_terms,
                                            sortTerms=sort_terms),
                                nsmap=self.mapping_registry.namespace_map)
        coll_data_el.append(q_el)
        # Total results.
        tr_tag = '{%s}%s' % (XML_NS_OPEN_SEARCH, 'totalResults')
        setattr(coll_data_el, tr_tag, str(len(collection)))
        if not collection.slice is None:
            # Start index.
            si_tag = '{%s}%s' % (XML_NS_OPEN_SEARCH, 'startIndex')
            setattr(coll_data_el, si_tag, str(collection.slice.start))
            # Page size.
            ps_tag = '{%s}%s' % (XML_NS_OPEN_SEARCH, 'itemsPerPage')
            setattr(coll_data_el, ps_tag, str(collection.slice.stop -
                                              collection.slice.start))


class AtomMappingRegistry(XmlMappingRegistry):
    NS_MAP = dict(opensearch=XML_NS_OPEN_SEARCH)
    mapping_class = AtomMapping

    def _initialize(self):
        # Create mappings for Member and Collection resource bases classes.
        atom_opts = dict(xml_schema='everest:schemata/atom.xsd',
                         xml_ns=XML_NS_ATOM,
                         xml_prefix=XML_PREFIX_ATOM)
        mb_config = \
            self.configuration_class(options=dict(list(atom_opts.items()) +
                                                  [('xml_tag', 'entry')]))
        mb_mp = self.create_mapping(Member, mb_config)
        self.set_mapping(mb_mp)
        coll_config = \
            self.configuration_class(options=dict(list(atom_opts.items()) +
                                                  [('xml_tag', 'feed')]))
        coll_mp = self.create_mapping(Collection, coll_config)
        self.set_mapping(coll_mp)

    @property
    def namespace_map(self):
        atom_ns_map = \
            getattr(XmlMappingRegistry, 'namespace_map').__get__(self)
        xml_mp_reg = get_mapping_registry(XmlMime)
        xml_ns_map = xml_mp_reg.namespace_map
        atom_ns_map.update(xml_ns_map)
        # Make ATOM namespace the default.
        atom_ns_map.pop(XML_PREFIX_ATOM, None)
        atom_ns_map[None] = XML_NS_ATOM
        return atom_ns_map


AtomRepresenterConfiguration = XmlRepresenterConfiguration
