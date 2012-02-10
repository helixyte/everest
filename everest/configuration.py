"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Configurators for the various subsystems of :mod:`everest`.

Created on Jun 22, 2011.
"""

from everest.entities.aggregates import MemoryAggregateImpl
from everest.entities.aggregates import OrmAggregateImpl
from everest.entities.base import Aggregate
from everest.entities.interfaces import IAggregate
from everest.entities.interfaces import IAggregateImplementationRegistry
from everest.entities.interfaces import IEntity
from everest.entities.repository import AggregateImplementationRegistry
from everest.entities.repository import EntityRepository
from everest.entities.system import Message
from everest.interfaces import IDefaultRepository
from everest.interfaces import IMessage
from everest.interfaces import IRepository
from everest.interfaces import IResourceUrlConverter
from everest.querying.base import EXPRESSION_KINDS
from everest.querying.filtering import CqlFilterSpecificationVisitor
from everest.querying.filtering import EvalFilterSpecificationVisitor
from everest.querying.filtering import FilterSpecificationBuilder
from everest.querying.filtering import FilterSpecificationDirector
from everest.querying.filtering import SqlFilterSpecificationVisitor
from everest.querying.interfaces import IFilterSpecificationBuilder
from everest.querying.interfaces import IFilterSpecificationDirector
from everest.querying.interfaces import IFilterSpecificationFactory
from everest.querying.interfaces import IFilterSpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationBuilder
from everest.querying.interfaces import IOrderSpecificationDirector
from everest.querying.interfaces import IOrderSpecificationFactory
from everest.querying.interfaces import IOrderSpecificationVisitor
from everest.querying.ordering import CqlOrderSpecificationVisitor
from everest.querying.ordering import EvalOrderSpecificationVisitor
from everest.querying.ordering import OrderSpecificationBuilder
from everest.querying.ordering import OrderSpecificationDirector
from everest.querying.ordering import SqlOrderSpecificationVisitor
from everest.querying.specifications import FilterSpecificationFactory
from everest.querying.specifications import OrderSpecificationFactory
from everest.repository import REPOSITORIES
from everest.representers.interfaces import IDataElementRegistry
from everest.representers.interfaces import IRepresenter
from everest.resources.base import Collection
from everest.resources.base import Resource
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IService
from everest.resources.persisters import DummyPersister
from everest.resources.persisters import FileSystemPersister
from everest.resources.persisters import OrmPersister
from everest.resources.repository import ResourceRepository
from everest.resources.repository import new_memory_repository
from everest.resources.service import Service
from everest.resources.system import MessageMember
from everest.url import ResourceUrlConverter
from repoze.bfg.configuration import Configurator as BfgConfigurator
from repoze.bfg.interfaces import IRequest
from repoze.bfg.path import caller_package
from zope.component.interfaces import IFactory # pylint: disable=E0611,F0401
from zope.interface import alsoProvides as also_provides # pylint: disable=E0611,F0401
from zope.interface import classImplements as class_implements # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['Configurator',
           ]


class Configurator(BfgConfigurator):
    """
    Configurator for everest.
    """

    def __init__(self,
                 registry=None,
                 package=None,
                 # Entity level services.
                 aggregate_implementation_registry=None,
                 filter_specification_factory=None,
                 order_specification_factory=None,
                 # Application level services.
                 service=None,
                 filter_builder=None,
                 filter_director=None,
                 cql_filter_specification_visitor=None,
                 sql_filter_specification_visitor=None,
                 eval_filter_specification_visitor=None,
                 order_builder=None,
                 order_director=None,
                 cql_order_specification_visitor=None,
                 sql_order_specification_visitor=None,
                 eval_order_specification_visitor=None,
                 url_converter=None,
                 **kw
                 ):
        if package is None:
            package = caller_package()
        BfgConfigurator.__init__(self,
                                 registry=registry, package=package, **kw)
        if registry is None:
            self.__setup(aggregate_implementation_registry,
                         filter_specification_factory,
                         order_specification_factory,
                         service,
                         filter_builder,
                         filter_director,
                         cql_filter_specification_visitor,
                         sql_filter_specification_visitor,
                         eval_filter_specification_visitor,
                         order_builder,
                         order_director,
                         cql_order_specification_visitor,
                         sql_order_specification_visitor,
                         eval_order_specification_visitor,
                         url_converter)

    def get_registered_utility(self, *args, **kw):
        """
        Convenience method for obtaining a utility from the registry.
        """
        return self.registry.getUtility(*args, **kw) # pylint: disable=E1103

    def query_registered_utilities(self, *args, **kw):
        """
        Convenience method for querying a utility from the registry.
        """
        return self.registry.queryUtility(*args, **kw) # pylint: disable=E1103

    def setup_registry(self,
                       aggregate_implementation_registry=None,
                       filter_specification_factory=None,
                       order_specification_factory=None,
                       service=None,
                       filter_specification_builder=None,
                       filter_specification_director=None,
                       cql_filter_specification_visitor=None,
                       sql_filter_specification_visitor=None,
                       eval_filter_specification_visitor=None,
                       order_specification_builder=None,
                       order_specification_director=None,
                       cql_order_specification_visitor=None,
                       sql_order_specification_visitor=None,
                       eval_order_specification_visitor=None,
                       url_converter=None,
                       **kw):
        BfgConfigurator.setup_registry(self, **kw)
        self.__setup(aggregate_implementation_registry,
                     filter_specification_factory,
                     order_specification_factory,
                     service,
                     filter_specification_builder,
                     filter_specification_director,
                     cql_filter_specification_visitor,
                     sql_filter_specification_visitor,
                     eval_filter_specification_visitor,
                     order_specification_builder,
                     order_specification_director,
                     cql_order_specification_visitor,
                     sql_order_specification_visitor,
                     eval_order_specification_visitor,
                     url_converter)

    def add_repository(self, name, persister_cls,
                       default_aggregate_implementation=None,
                       make_default=False, configuration=None, _info=u'',):
        if not self.get_registered_utility(IRepository, name) is None:
            raise ValueError('Duplicate repository name "%s".' % name)
        if configuration is None:
            configuration = {}
        custom_persister = persister_cls(name)
        custom_ent_repo = EntityRepository(custom_persister)
        if not default_aggregate_implementation is None:
            custom_ent_repo.set_default_implementation(
                                            default_aggregate_implementation)
        custom_rc_repo = ResourceRepository(custom_ent_repo)
        custom_rc_repo.configure(**configuration) # pylint: disable=W0142
        if make_default:
            self._register_utility(custom_rc_repo, IDefaultRepository)

    def add_resource(self, interface, member, entity,
                     collection=None, aggregate=None,
                     entity_adapter=None, aggregate_adapter=None,
                     collection_root_name=None, collection_title=None,
                     expose=True, repository=None, _info=u''):
        if not (isinstance(member, type)
                and IMemberResource in provided_by(object.__new__(member))):
            raise ValueError('The member must be a class that implements '
                             'IMemberResource.')
        if not (isinstance(entity, type)
                and IEntity in provided_by(object.__new__(entity))):
            raise ValueError('The entity must be a class that implements '
                             'IEntity.')
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
        elif not (isinstance(aggregate, type)
                  and IAggregate in provided_by(object.__new__(aggregate))):
            raise ValueError('The aggregate must be a class that implements '
                             'IAggregate.')
        # Override the root name and title the collection, if requested.
        if not collection_root_name is None:
            collection.root_name = collection_root_name
        if not collection_title is None:
            collection.title = collection_title
        if expose:
            srvc = self.query_registered_utilities(IService)
            if srvc is None:
                raise ValueError('Need a IService utility to expose a '
                                 'resource.')
            if collection.root_name is None:
                raise ValueError('To expose a collection resource in the '
                                 'service (=root), a root name is required.')
        # Register the entity instance -> member instance adapter.
        if entity_adapter is None:
            mb_factory = member.create_from_entity
        else:
            mb_factory = entity_adapter
        self._register_adapter(mb_factory, (interface,), IMemberResource,
                               info=_info)
        # Register the aggregate instance -> collection instance adapter.
        if aggregate_adapter is None:
            agg_factory = collection.create_from_aggregate
        else:
            agg_factory = aggregate_adapter
        self._register_adapter(agg_factory, (interface,), ICollectionResource,
                          info=_info)
        # Register adapter object implementing interface -> member class
        self._register_adapter(lambda obj: member,
                               required=(interface,),
                               provided=IMemberResource,
                               name='member-class',
                               info=_info)
        # Register adapter object implementing interface -> collection class
        self._register_adapter(lambda obj: collection,
                               required=(interface,),
                               provided=ICollectionResource,
                               name='collection-class',
                               info=_info)
        # Register adapter object implementing interface -> member class
        self._register_adapter(lambda obj: entity,
                               required=(interface,),
                               provided=IEntity,
                               name='entity-class',
                               info=_info)
        # Register adapter object implementing interface -> collection class
        self._register_adapter(lambda obj: aggregate,
                               required=(interface,),
                               provided=IAggregate,
                               name='aggregate-class',
                               info=_info)
        # Register utility interface -> member class
        self._register_utility(member, interface,
                               name='member-class', info=_info)
        # Register utility interface -> collection class
        self._register_utility(collection, interface,
                               name='collection-class', info=_info)
        # Register utility interface -> entity class
        self._register_utility(entity, interface,
                               name='entity-class', info=_info)
        # Register utility interface -> aggregate class
        self._register_utility(aggregate, interface,
                               name='aggregate-class', info=_info)
        # Attach the marker interface to the registered resource classes, if
        # necessary, so the instances will provide it.
        if not interface in provided_by(member):
            class_implements(member, interface)
        if not interface in provided_by(collection):
            class_implements(collection, interface)
        if not interface in provided_by(entity):
            class_implements(entity, interface)
        if not interface in provided_by(aggregate):
            class_implements(aggregate, interface)
        # This enables us to pass a class instead of
        # an interface or instance to the various adapters.
        also_provides(member, interface)
        also_provides(collection, interface)
        also_provides(entity, interface)
        also_provides(aggregate, interface)
        # Configure the persister adapter.
        if repository is None:
            repo = self.get_registered_utility(IDefaultRepository)
        else:
            repo = self.get_registered_utility(IRepository, repository)
        repo.manage(collection)
        if not repo.is_initialized:
            # Make sure the persister gets initialized.
            repo.initialize()
        self._register_adapter(lambda obj: repo,
                               required=(interface,),
                               provided=IRepository,
                               info=_info)
        # Expose (=register with the service) if requested.
        if expose:
            srvc.register(interface)

    def add_representer(self, resource, content_type, configuration=None,
                        _info=u''):
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
        rpr_cls = self.get_registered_utility(IRepresenter, utility_name)
        de_reg = self.query_registered_utilities(IDataElementRegistry,
                                                 utility_name)
        if de_reg is None:
            # A sad attempt at providing a singleton that lives as long
            # as the associated (zope) registry: The first time this is
            # called with a fresh registry, a data element registry is
            # instantiated and then registered as a utility.
            de_reg = rpr_cls.make_data_element_registry()
            self._register_utility(de_reg, IDataElementRegistry,
                                   name=utility_name)
        de_cls = de_reg.create_data_element_class(resource, configuration)
        de_reg.set_data_element_class(de_cls)
        # Register adapter resource, MIME name -> representer.
        self._register_adapter(rpr_cls.create_from_resource,
                               (resource,),
                               IRepresenter,
                               name=utility_name,
                               info=_info)

    def _register_utility(self, *args, **kw):
        return self.registry.registerUtility(*args, **kw) # pylint: disable=E1103

    def _register_adapter(self, *args, **kw):
        return self.registry.registerAdapter(*args, **kw) # pylint: disable=E1103

    def __setup(self,
                aggregate_implementation_registry,
                filter_specification_factory,
                order_specification_factory,
                service,
                filter_specification_builder,
                filter_specification_director,
                cql_filter_specification_visitor,
                sql_filter_specification_visitor,
                eval_filter_specification_visitor,
                order_specification_builder,
                order_specification_director,
                cql_order_specification_visitor,
                sql_order_specification_visitor,
                eval_order_specification_visitor,
                url_converter):
        # Set up the two builtin entity repositories.
        # ... aggregate implementation registry.
        if aggregate_implementation_registry is None:
            aggregate_implementation_registry = \
                                    AggregateImplementationRegistry()
            aggregate_implementation_registry.register(MemoryAggregateImpl)
            aggregate_implementation_registry.register(OrmAggregateImpl)
            self._register_utility(aggregate_implementation_registry,
                                   IAggregateImplementationRegistry)

        # ... ORM repository
        orm_repo = self.__make_repo(REPOSITORIES.ORM, OrmPersister,
                                    aggregate_implementation_registry,
                                    OrmAggregateImpl,
                                    [('db_string', 'orm_dbstring')])
        self._register_utility(orm_repo, IRepository,
                               name=REPOSITORIES.ORM)
        # ... MEMORY repository. By default this is used as the default for
        #     all resources that do not specify a repository.
        mem_repo = self.__make_repo(REPOSITORIES.MEMORY, DummyPersister,
                                    aggregate_implementation_registry,
                                    MemoryAggregateImpl, [])
        self._register_utility(mem_repo, IRepository,
                               name=REPOSITORIES.MEMORY)
        self._register_utility(mem_repo, IDefaultRepository)
        # ... FILE_SYSTEM repository.
        fs_repo = self.__make_repo(REPOSITORIES.FILE_SYSTEM,
                                   FileSystemPersister,
                                   aggregate_implementation_registry,
                                   MemoryAggregateImpl,
                                   [('directory', 'fs_directory'),
                                    ('content_type', 'fs_contenttype')])
        self._register_utility(fs_repo, IRepository,
                               name=REPOSITORIES.FILE_SYSTEM)
        # Register a factory for new memory repositories.
        self._register_utility(new_memory_repository, IFactory,
                               name=REPOSITORIES.MEMORY)
        # Set up filter and order specification factories.
        if filter_specification_factory is None:
            filter_specification_factory = FilterSpecificationFactory()
        self._register_utility(filter_specification_factory,
                               IFilterSpecificationFactory)
        if order_specification_factory is None:
            order_specification_factory = OrderSpecificationFactory()
        self._register_utility(order_specification_factory,
                               IOrderSpecificationFactory)
        # Set up the service.
        if service is None:
            service = Service()
        self._register_utility(service, IService)
        # Set up filter and order specification builders, directors, visitors.
        if filter_specification_builder is None:
            filter_specification_builder = FilterSpecificationBuilder
        self._register_utility(filter_specification_builder,
                               IFilterSpecificationBuilder)
        if filter_specification_director is None:
            filter_specification_director = FilterSpecificationDirector
        self._register_utility(filter_specification_director,
                               IFilterSpecificationDirector)
        if cql_filter_specification_visitor is None:
            cql_filter_specification_visitor = CqlFilterSpecificationVisitor
        self._register_utility(cql_filter_specification_visitor,
                               IFilterSpecificationVisitor,
                              name=EXPRESSION_KINDS.CQL)
        if sql_filter_specification_visitor is None:
            sql_filter_specification_visitor = SqlFilterSpecificationVisitor
        self._register_utility(sql_filter_specification_visitor,
                               IFilterSpecificationVisitor,
                               name=EXPRESSION_KINDS.SQL)
        if eval_filter_specification_visitor is None:
            eval_filter_specification_visitor = EvalFilterSpecificationVisitor
        self._register_utility(eval_filter_specification_visitor,
                               IFilterSpecificationVisitor,
                               name=EXPRESSION_KINDS.EVAL)
        if order_specification_builder is None:
            order_specification_builder = OrderSpecificationBuilder
        self._register_utility(order_specification_builder,
                               IOrderSpecificationBuilder)
        if order_specification_director is None:
            order_specification_director = OrderSpecificationDirector
        self._register_utility(order_specification_director,
                               IOrderSpecificationDirector)
        if cql_order_specification_visitor is None:
            cql_order_specification_visitor = CqlOrderSpecificationVisitor
        self._register_utility(cql_order_specification_visitor,
                               IOrderSpecificationVisitor,
                               name=EXPRESSION_KINDS.CQL)
        if sql_order_specification_visitor is None:
            sql_order_specification_visitor = SqlOrderSpecificationVisitor
        self._register_utility(sql_order_specification_visitor,
                               IOrderSpecificationVisitor,
                               name=EXPRESSION_KINDS.SQL)
        if eval_order_specification_visitor is None:
            eval_order_specification_visitor = EvalOrderSpecificationVisitor
        self._register_utility(eval_order_specification_visitor,
                               IOrderSpecificationVisitor,
                               name=EXPRESSION_KINDS.EVAL)
        # URL converter adapter.
        if url_converter is None:
            url_converter = ResourceUrlConverter
        self._register_adapter(url_converter, (IRequest,),
                               IResourceUrlConverter)
        # Register system resources provided as a service to the application.
        self.add_resource(IMessage, MessageMember, Message,
                          aggregate=MemoryAggregateImpl,
                          repository=REPOSITORIES.MEMORY,
                          collection_root_name='_messages')

    def __make_repo(self, name, prst_cls, agg_impl_reg, agg_impl_cls,
                    setting_info):
        settings = self.get_settings()
        persister = prst_cls(name)
        entity_repository = \
                    EntityRepository(persister,
                                     implementation_registry=agg_impl_reg)
        entity_repository.set_default_implementation(agg_impl_cls)
        resource_repository = ResourceRepository(entity_repository)
        config = dict([(name, settings.get(key))
                       for (name, key) in setting_info
                       if not settings.get(key, None) is None])
        resource_repository.configure(**config) # pylint: disable=W0142
        return resource_repository

