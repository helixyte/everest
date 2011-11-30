"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 22, 2011.
"""

from everest.entities.aggregates import MemoryRelationAggregateImpl
from everest.entities.aggregates import MemoryRootAggregateImpl
from everest.entities.base import Aggregate
from everest.entities.base import Entity
from everest.entities.interfaces import IAggregate
from everest.entities.interfaces import IEntity
from everest.entities.interfaces import IRelationAggregateImplementation
from everest.entities.interfaces import IRootAggregateImplementation
from everest.entities.system import Message
from everest.filtering import FilterSpecificationBuilder
from everest.filtering import FilterSpecificationDirector
from everest.interfaces import ICqlFilterSpecificationVisitor
from everest.interfaces import ICqlOrderSpecificationVisitor
from everest.interfaces import IFilterSpecificationBuilder
from everest.interfaces import IFilterSpecificationDirector
from everest.interfaces import IFilterSpecificationFactory
from everest.interfaces import IMessage
from everest.interfaces import IOrderSpecificationBuilder
from everest.interfaces import IOrderSpecificationDirector
from everest.interfaces import IOrderSpecificationFactory
from everest.interfaces import IQueryFilterSpecificationVisitor
from everest.interfaces import IQueryOrderSpecificationVisitor
from everest.interfaces import IResourceUrlConverter
from everest.ordering import OrderSpecificationBuilder
from everest.ordering import OrderSpecificationDirector
from everest.representers.interfaces import IDataElementRegistry
from everest.representers.interfaces import IRepresenter
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.base import Resource
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IService
from everest.resources.service import Service
from everest.resources.system import MessageMember
from everest.specifications import FilterSpecificationFactory
from everest.specifications import OrderSpecificationFactory
from everest.url import ResourceUrlConverter
from everest.visitors import CqlFilterSpecificationVisitor
from everest.visitors import CqlOrderSpecificationVisitor
from everest.visitors import QueryFilterSpecificationVisitor
from everest.visitors import QueryOrderSpecificationVisitor
from repoze.bfg.configuration import Configurator as BfgConfigurator
from repoze.bfg.interfaces import IRequest
from repoze.bfg.path import caller_package
from zope.interface import classImplements as class_implements # pylint: disable=E0611,F0401
from zope.interface import directlyProvides as directly_provides # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['Configurator',
           ]


class Configurator(BfgConfigurator):
    """
    Specialized configurator for resources.
    """
    def __init__(self,
                 registry=None,
                 package=None,
                 service=None,
                 # filters specification utilities.
                 filter_specification_factory=None,
                 filter_builder=None,
                 filter_director=None,
                 cql_filter_specification_visitor=None,
                 query_filter_specification_visitor=None,
                 # order specification utilities.
                 order_specification_factory=None,
                 order_builder=None,
                 order_director=None,
                 cql_order_specification_visitor=None,
                 query_order_specification_visitor=None,
                 # aggregate utilities.
                 root_aggregate_implementation=None,
                 relation_aggregate_implementation=None,
                 url_converter=None,
                 **kw):
        if package is None:
            package = caller_package()
        BfgConfigurator.__init__(self, registry=registry, package=package,
                                 **kw)
        if registry is None:
            self.__setup_everest(service,
                                 filter_specification_factory,
                                 filter_builder,
                                 filter_director,
                                 cql_filter_specification_visitor,
                                 query_filter_specification_visitor,
                                 order_specification_factory,
                                 order_builder,
                                 order_director,
                                 cql_order_specification_visitor,
                                 query_order_specification_visitor,
                                 root_aggregate_implementation,
                                 relation_aggregate_implementation,
                                 url_converter)

    def setup_registry(self,
                       service=None,
                       # filters specification utilities.
                       filter_specification_factory=None,
                       filter_builder=None,
                       filter_director=None,
                       cql_filter_specification_visitor=None,
                       query_filter_specification_visitor=None,
                       # order specification utilities.
                       order_specification_factory=None,
                       order_builder=None,
                       order_director=None,
                       cql_order_specification_visitor=None,
                       query_order_specification_visitor=None,
                       # aggregate utilities.
                       root_aggregate_implementation=None,
                       relation_aggregate_implementation=None,
                       url_converter=None,
                       **kw):
        BfgConfigurator.setup_registry(self, **kw)
        self.__setup_everest(service,
                             filter_specification_factory,
                             filter_builder,
                             filter_director,
                             cql_filter_specification_visitor,
                             query_filter_specification_visitor,
                             order_specification_factory,
                             order_builder,
                             order_director,
                             cql_order_specification_visitor,
                             query_order_specification_visitor,
                             root_aggregate_implementation,
                             relation_aggregate_implementation,
                             url_converter)

    def add_resource(self, interface, member, entity,
                     collection=None, aggregate=None,
                     entity_adapter=None, aggregate_adapter=None,
                     collection_root_name=None, collection_title=None,
                     expose=True, _info=u''):
        """
        Adds a collection resource.

        This can also be invoked through ZCML using the
          :function:`everest.directives.resource` directive.
        """
        if not issubclass(member, Member):
            raise ValueError('The member must be a subclass '
                             'of member.')
        if not issubclass(entity, Entity):
            raise ValueError('The entity must be a subclass '
                             'of Entity.')
        if collection is None:
            collection = type('%sCollection' % member.__name__,
                              (Collection,), {})
            if collection_title is None:
                collection.title = 'Collection of %s' % member.__name__
        elif not issubclass(collection, Collection):
            raise ValueError('The collection must be a subclass '
                             'of Collection.')
        if aggregate is None:
            aggregate = type('%sAggregate' % entity.__name__,
                             (Aggregate,), {})
        elif not IAggregate in provided_by(object.__new__(aggregate)):
            raise ValueError('The entity aggregate must implement IAggregate.')
        if expose:
            srvc = self.registry.queryUtility(IService) # pylint: disable=E1103
            if srvc is None:
                raise ValueError('Need a IService utility to expose a '
                                 'resource.')
        # Override the root name and title the collection, if requested.
        if not collection_root_name is None:
            collection.root_name = collection_root_name
        if expose and collection.root_name is None:
            raise ValueError('To expose a collection resource in the '
                             'service (=root), a root name is required.')
        if not collection_title is None:
            collection.title = collection_title
        # Shortcuts to ease pylint.
        register_adapter = self.registry.registerAdapter # pylint: disable=E1103
        register_utility = self.registry.registerUtility # pylint: disable=E1103
        # Register the entity instance -> member instance adapter.
        if entity_adapter is None:
            mb_factory = member.create_from_entity
        else:
            mb_factory = entity_adapter
        register_adapter(mb_factory, (interface,), IMemberResource,
                         info=_info)
        # Register the aggregate instance -> collection instance adapter.
        if aggregate_adapter is None:
            agg_factory = collection.create_from_aggregate
        else:
            agg_factory = aggregate_adapter
        register_adapter(agg_factory, (interface,), ICollectionResource,
                        info=_info)
        # Register adapter object implementing interface -> member class
        register_adapter(lambda obj: member,
                         required=(interface,),
                         provided=IMemberResource,
                         name='member-class',
                         info=_info)
        # Register adapter object implementing interface -> collection class
        register_adapter(lambda obj: collection,
                         required=(interface,),
                         provided=ICollectionResource,
                         name='collection-class',
                         info=_info)
        # Register adapter object implementing interface -> member class
        register_adapter(lambda obj: entity,
                         required=(interface,),
                         provided=IEntity,
                         name='entity-class',
                         info=_info)
        # Register adapter object implementing interface -> collection class
        register_adapter(lambda obj: aggregate,
                         required=(interface,),
                         provided=IAggregate,
                         name='aggregate-class',
                         info=_info)
        # Register utility interface -> member class
        register_utility(member, interface, name='member-class', info=_info)
        # Register utility interface -> collection class
        register_utility(collection, interface,
                         name='collection-class', info=_info)
        # Register utility interface -> entity class
        register_utility(entity, interface, name='entity-class', info=_info)
        # Register utility interface -> aggregate class
        register_utility(aggregate, interface,
                         name='aggregate-class', info=_info)
        # Attach the marker interface to the registered resource classes, if
        # necessary.
        if not interface in provided_by(member):
            class_implements(member, interface)
        if not interface in provided_by(collection):
            class_implements(collection, interface)
        if not interface in provided_by(entity):
            class_implements(entity, interface)
        if not interface in provided_by(aggregate):
            class_implements(aggregate, interface)
        # This enables us to pass the collection  or member class instead of
        # an interface or instance to the various adapters.
        directly_provides(member, interface)
        directly_provides(collection, interface)
#        directly_provides(entity, interface)
#        directly_provides(aggregate, interface)
        # Expose (=register with the service) if requested.
        if expose:
            srvc.register(interface)

    def add_representer(self, resource, content_type, configuration=None,
                        _info=u''):
        """
        Adds a representer.

        This can also be invoked through the
          :function:`everest.directives.representer` directive.
        """
        # If we were passed a class, instantiate it.
        if type(configuration) is type:
            configuration = configuration()
        # FIXME: Should we allow interfaces here? # pylint: disable=W0511
        if not issubclass(resource, Resource):
            raise ValueError('Representers can only be registered for classes '
                             'inheriting from the Resource base class.')
        # Register customized data element class for the representer
        # class registered for the given content type.
        utility_name = content_type.mime_string
        rpr_cls = self.registry.getUtility(IRepresenter, utility_name) # pylint: disable=E1103
        de_reg = self.registry.queryUtility(IDataElementRegistry, utility_name) # pylint: disable=E1103
        if de_reg is None:
            # A sad attempt at providing a singleton that lives as long
            # as the associated (zope) registry: The first time this is
            # called with a fresh registry, a data element registry is
            # instantiated and then registered as a utility.
            de_reg = rpr_cls.make_data_element_registry()
            self.registry.registerUtility(de_reg, IDataElementRegistry, # pylint: disable=E1103
                                          name=utility_name)
        de_cls = de_reg.create_data_element_class(resource, configuration)
        de_reg.set_data_element_class(de_cls)
        # Register adapter resource, MIME name -> representer;
        self.registry.registerAdapter(rpr_cls.create_from_resource, # pylint: disable=E1103
                                      (resource,),
                                      IRepresenter,
                                      name=utility_name,
                                      info=_info)

    def __setup_everest(self,
                        service,
                        filter_specification_factory,
                        filter_builder,
                        filter_director,
                        cql_filter_specification_visitor,
                        query_filter_specification_visitor,
                        order_specification_factory,
                        order_builder,
                        order_director,
                        cql_order_specification_visitor,
                        query_order_specification_visitor,
                        root_aggregate_implementation,
                        relation_aggregate_implementation,
                        url_converter):
        register_utility = self.registry.registerUtility # pylint: disable=E1103
        register_adapter = self.registry.registerAdapter # pylint: disable=E1103
        if service is None:
            service = Service()
        register_utility(service, IService)
        # Filter specification utilities.
        if filter_specification_factory is None:
            filter_specification_factory = FilterSpecificationFactory()
        register_utility(filter_specification_factory,
                         IFilterSpecificationFactory)
        if filter_builder is None:
            filter_builder = FilterSpecificationBuilder
        register_utility(filter_builder, IFilterSpecificationBuilder)
        if filter_director is None:
            filter_director = FilterSpecificationDirector
        register_utility(filter_director, IFilterSpecificationDirector)
        if cql_filter_specification_visitor is None:
            cql_filter_specification_visitor = CqlFilterSpecificationVisitor
        register_utility(cql_filter_specification_visitor,
                         ICqlFilterSpecificationVisitor)
        if query_filter_specification_visitor is None:
            query_filter_specification_visitor = QueryFilterSpecificationVisitor
        register_utility(query_filter_specification_visitor,
                         IQueryFilterSpecificationVisitor)
        # Order specification utilitites.
        if order_specification_factory is None:
            order_specification_factory = OrderSpecificationFactory()
        register_utility(order_specification_factory,
                         IOrderSpecificationFactory)
        if order_builder is None:
            order_builder = OrderSpecificationBuilder
        register_utility(order_builder, IOrderSpecificationBuilder)
        if order_director is None:
            order_director = OrderSpecificationDirector
        register_utility(order_director, IOrderSpecificationDirector)
        if cql_order_specification_visitor is None:
            cql_order_specification_visitor = CqlOrderSpecificationVisitor
        register_utility(cql_order_specification_visitor,
                         ICqlOrderSpecificationVisitor)
        if query_order_specification_visitor is None:
            query_order_specification_visitor = QueryOrderSpecificationVisitor
        register_utility(query_order_specification_visitor,
                         IQueryOrderSpecificationVisitor)
        # Aggregate utilities.
        if root_aggregate_implementation is None:
            root_aggregate_implementation = MemoryRootAggregateImpl
        register_utility(root_aggregate_implementation,
                         IRootAggregateImplementation)
        if relation_aggregate_implementation is None:
            relation_aggregate_implementation = MemoryRelationAggregateImpl
        register_utility(relation_aggregate_implementation,
                         IRelationAggregateImplementation)
        # URL converter adapter.
        if url_converter is None:
            url_converter = ResourceUrlConverter
        register_adapter(url_converter, (IRequest,), IResourceUrlConverter)
        # Register system resources.
        self.add_resource(IMessage, MessageMember, Message,
                          aggregate=MemoryRootAggregateImpl,
                          collection_root_name='_messages')

    def __find_interface(self, cls, base_interface):
        # Finds the first interface provided by `cls` that is a
        # subclass of `base_interface`.
        if issubclass(cls, base_interface):
            i_cls = cls
        else:
            i_cls = None
            for prov_i_cls in provided_by(object.__new__(cls)):
                if issubclass(prov_i_cls, base_interface):
                    i_cls = prov_i_cls
                    break
        if i_cls is None:
            raise ValueError('The specified resource is neither a subclass of '
                             '%(cls)s nor a class implementing %(cls)s.' %
                             dict(cls=cls))
        return i_cls
