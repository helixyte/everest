"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

ATOM representers.

Created on May 19, 2011.
"""

from everest.mime import AtomMime
from everest.mime import XmlMime
from everest.representers.base import DataElementGenerator
from everest.representers.base import DataElementParser
from everest.representers.base import ResourceRepresenter
from everest.representers.interfaces import IDataElementRegistry
from everest.representers.utils import as_representer
from everest.representers.xml import XmlDataElementRegistry
from everest.representers.xml import XmlRepresentationGenerator
from everest.representers.xml import XmlRepresenterConfiguration
from everest.url import UrlPartsConverter
from repoze.bfg.threadlocal import get_current_registry

__docformat__ = 'reStructuredText en'
__all__ = ['AtomDataElementRegistry',
           'AtomResourceRepresenter',
           ]

XML_NS_OPEN_SEARCH = 'http://a9.com/-/spec/opensearch/1.1/'


class AtomResourceRepresenter(ResourceRepresenter):

    content_type = AtomMime

    def from_stream(self, stream):
        # We do not support parsing ATOM representations.
        raise NotImplementedError('Not implemented.')

    def parse(self, parser):
        # We do not support parsing ATOM representations.
        raise NotImplementedError('Not implemented.')

    @classmethod
    def make_data_element_registry(cls):
        return AtomDataElementRegistry()

    def _make_representation_parser(self, stream, resource_class):
        # We do not support parsing ATOM representations.
        raise NotImplementedError('Not implemented.')

    def _make_representation_generator(self, stream, resource_class, **config):
        generator = XmlRepresentationGenerator(stream, resource_class)
        generator.configure(**config)
        return generator

    def _make_data_element_parser(self):
        return DataElementParser()

    def _make_data_element_generator(self):
        return AtomDataElementGenerator(self._data_element_registry)


class AtomDataElementGenerator(DataElementGenerator):

    # FIXME: Make the hypermedia type configurable. pylint: disable=W0511
    VND_MIME = 'application/vnd.cenix+xml'

    def _inject_member_resource(self, member, nesting_level, mapping_info):
        # Build a representer for the content. Only XML content is supported
        # for now.
        member_rpr = as_representer(member, XmlMime.mime_string)
        if nesting_level > 1:
            raise ValueError('Can only encode top level members in ATOM.')
        de_cls = \
          self._data_element_registry.get_data_element_class(type(member))
        data_el = de_cls.create_from_resource(member)
        # Fill in ATOM tags.
        # FIXME: Should not use etree API here pylint: disable=W0511
        data_el.title = member.title
        data_el.id = member.urn
        self.__append_links(data_el, member.links)
        content_data_el = \
            member_rpr.data_from_resource(member,
                                          mapping_info=mapping_info)
        type_string = '%s;type=%s' % (self.VND_MIME, member.__class__.__name__)
        cnt_wrapper_el = data_el.makeelement('content',
                                             type=type_string)
        cnt_wrapper_el.append(content_data_el)
        data_el.append(cnt_wrapper_el)
        return data_el

    def _inject_collection_resource(self, collection, nesting_level,
                                    mapping_info):
        if nesting_level > 0:
            raise ValueError('Can only encode top level members in ATOM.')
        coll_de_cls = self._data_element_registry.get_data_element_class(
                                                         type(collection))
        coll_data_el = coll_de_cls.create_from_resource(collection)
        # Fill in ATOM tags.
        coll_data_el.title = collection.title
        coll_data_el.subtitle = collection.description
        coll_data_el.generator = collection.title
        coll_data_el.generator.set('uri', collection.path)
        #
        coll_data_el.id = collection.urn
        # FIXME: Make the media type configurable. pylint: disable=W0511
        type_string = '%s;type=%s' % (self.VND_MIME,
                                      collection.__class__.__name__)
        cnt_type_el = coll_data_el.makeelement('content_type',
                                               name=type_string)
        coll_data_el.append(cnt_type_el)
        #
        self.__append_opensearch_elements(coll_data_el, collection)
        self.__append_links(coll_data_el, collection.links)
        # We extract the collection mapper's attribute mapping to the
        # member representer so that attribute serialization works as
        # expected.
        reg = get_current_registry()
        de_reg = reg.getUtility(IDataElementRegistry, XmlMime.mime_string)
        cnt_de_cls = de_reg.get_data_element_class(type(collection))
        mp_info = cnt_de_cls.mapper.get_config_option('mapping')
        for member in collection:
            member_data_el = self._inject_member_resource(member,
                                                          nesting_level + 1,
                                                          mp_info)
            coll_data_el.append(member_data_el)
        return coll_data_el

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
        elif collection.default_order:
            sort_terms = UrlPartsConverter.make_order_string(
                                                    collection.default_order)
        else:
            sort_terms = ''
        # Query.
        q_tag = '{%s}%s' % (XML_NS_OPEN_SEARCH, 'Query')
        q_el = \
            coll_data_el.makeelement(q_tag,
                                     role='request', searchTerms=search_terms,
                                     sortTerms=sort_terms)
        coll_data_el.append(q_el)
        # Total results.
        tr_tag = '{%s}%s' % (XML_NS_OPEN_SEARCH, 'totalResults')
        setattr(coll_data_el, tr_tag, str(len(collection)))
        # Start index.
        si_tag = '{%s}%s' % (XML_NS_OPEN_SEARCH, 'startIndex')
        setattr(coll_data_el, si_tag, str(collection.slice.start))
        # Page size.
        ps_tag = '{%s}%s' % (XML_NS_OPEN_SEARCH, 'itemsPerPage')
        setattr(coll_data_el, ps_tag,
                str(collection.slice.stop - collection.slice.start))


# Adapters creating representers from resource instances.

#FIXME this override does not work # pylint: disable=W0511
class AtomDataElementRegistry(XmlDataElementRegistry):

    NS_MAP = dict(opensearch=XML_NS_OPEN_SEARCH)


resource_adapter = AtomResourceRepresenter.create_from_resource


AtomRepresenterConfiguration = XmlRepresenterConfiguration
