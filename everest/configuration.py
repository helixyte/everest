"""
Configurator for everest.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 22, 2011.
"""
from everest.constants import RequestMethods
from everest.entities.interfaces import IEntity
from everest.entities.system import UserMessage
from everest.entities.traversal import DomainDataTraversalProxyAdapter
from everest.entities.traversal import LinkedDomainDataTraversalProxyAdapter
from everest.interfaces import IDataTraversalProxyAdapter
from everest.interfaces import IDataTraversalProxyFactory
from everest.interfaces import IResourceUrlConverter
from everest.interfaces import IUserMessage
from everest.interfaces import IUserMessageNotifier
from everest.messaging import UserMessageNotifier
from everest.mime import get_registered_representer_names
from everest.querying.base import EXPRESSION_KINDS
from everest.querying.filtering import CqlFilterSpecificationVisitor
from everest.querying.interfaces import IFilterSpecificationFactory
from everest.querying.interfaces import IFilterSpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationFactory
from everest.querying.interfaces import IOrderSpecificationVisitor
from everest.querying.ordering import CqlOrderSpecificationVisitor
from everest.querying.specifications import FilterSpecificationFactory
from everest.querying.specifications import OrderSpecificationFactory
from everest.renderers import RendererFactory
from everest.repositories.constants import REPOSITORY_DOMAINS
from everest.repositories.constants import REPOSITORY_TYPES
from everest.repositories.filesystem.repository import FileSystemRepository
from everest.repositories.interfaces import IRepository
from everest.repositories.interfaces import IRepositoryManager
from everest.repositories.manager import RepositoryManager
from everest.repositories.memory import ObjectFilterSpecificationVisitor
from everest.repositories.memory import ObjectOrderSpecificationVisitor
from everest.repositories.memory.repository import MemoryRepository
from everest.repositories.rdb import SqlFilterSpecificationVisitor
from everest.repositories.rdb import SqlOrderSpecificationVisitor
from everest.repositories.rdb.repository import RdbRepository
from everest.representers.atom import AtomResourceRepresenter
from everest.representers.base import MappingResourceRepresenter
from everest.representers.csv import CsvResourceRepresenter
from everest.representers.interfaces import ICollectionDataElement
from everest.representers.interfaces import ILinkedDataElement
from everest.representers.interfaces import IMemberDataElement
from everest.representers.interfaces import IRepresenterRegistry
from everest.representers.json import JsonResourceRepresenter
from everest.representers.registry import RepresenterRegistry
from everest.representers.traversal import DataElementDataTraversalProxyAdapter
from everest.representers.xml import XmlResourceRepresenter
from everest.resources.attributes import resource_attributes_injector
from everest.resources.base import Collection
from everest.resources.base import Resource
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IRelation
from everest.resources.interfaces import IService
from everest.resources.service import Service
from everest.resources.system import UserMessageMember
from everest.resources.utils import provides_member_resource
from everest.traversal import DataTraversalProxyFactory
from everest.url import ResourceUrlConverter
from everest.views.base import RepresentingResourceView
from everest.views.deletemember import DeleteMemberView
from everest.views.getcollection import GetCollectionView
from everest.views.getmember import GetMemberView
from everest.views.patchmember import PatchMemberView
from everest.views.postcollection import PostCollectionView
from everest.views.putmember import PutMemberView
from pyramid.compat import iteritems_
from pyramid.compat import string_types
from pyramid.config import Configurator as PyramidConfigurator
from pyramid.config.util import action_method
from pyramid.interfaces import IApplicationCreated
from pyramid.interfaces import IRendererFactory
from pyramid.interfaces import IRequest
from pyramid.path import DottedNameResolver
from pyramid.path import caller_package
from pyramid.registry import Registry
from pyramid_zcml import load_zcml
from zope.interface import alsoProvides as also_provides # pylint: disable=E0611,F0401
from zope.interface import classImplements as class_implements # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.interface.interfaces import IInterface # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['Configurator',
           ]


class Configurator(PyramidConfigurator):
    """
    Configurator for everest.
    """

    def __init__(self,
                 registry=None,
                 package=None,
                 autocommit=True,
                 # Entity level services.
                 filter_specification_factory=None,
                 order_specification_factory=None,
                 # Application level services.
                 service=None,
                 cql_filter_specification_visitor=None,
                 sql_filter_specification_visitor=None,
                 eval_filter_specification_visitor=None,
                 cql_order_specification_visitor=None,
                 sql_order_specification_visitor=None,
                 eval_order_specification_visitor=None,
                 url_converter=None,
                 **kw
                 ):
        if package is None:
            package = caller_package()
        call_setup = registry is None
        if call_setup:
            # Need to initialize our registry here to call our setup_registry
            # with the given custom option values rather than from the base
            # class constructor.
            # FIXME: There is some code duplication with Pyramid here.
            name_resolver = DottedNameResolver(package)
            package_name = name_resolver.get_package_name()
            registry = Registry(package_name)
            self.registry = registry
        # FIXME: Investigate why we need the "autocommit=True" flag here.
        PyramidConfigurator.__init__(self,
                                     registry=registry, package=package,
                                     autocommit=autocommit, **kw)
        # Set up configurator's load_zcml method.
        self.add_directive('load_zcml', load_zcml, action_wrap=False)
        if call_setup:
            self.setup_registry(
               filter_specification_factory=filter_specification_factory,
               order_specification_factory=order_specification_factory,
               service=service,
               cql_filter_specification_visitor=
                                    cql_filter_specification_visitor,
               sql_filter_specification_visitor=
                                    sql_filter_specification_visitor,
               eval_filter_specification_visitor=
                                    eval_filter_specification_visitor,
               cql_order_specification_visitor=
                                    cql_order_specification_visitor,
               sql_order_specification_visitor=
                                    sql_order_specification_visitor,
               eval_order_specification_visitor=
                                    eval_order_specification_visitor,
               url_converter=url_converter,
               **kw)

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

    def get_configuration_from_settings(self, setting_info):
        """
        Returns a dictionary with configuration names as keys and setting
        values extracted from this configurator's settings as values.

        :param setting_info: Sequence of 2-tuples containing the configuration
          name as the first and the setting name as the second element.
        """
        settings = self.get_settings()
        return dict([(name, settings.get(key))
                     for (name, key) in setting_info
                     if not settings.get(key, None) is None])

    def setup_registry(self,
                       filter_specification_factory=None,
                       order_specification_factory=None,
                       service=None,
                       cql_filter_specification_visitor=None,
                       sql_filter_specification_visitor=None,
                       eval_filter_specification_visitor=None,
                       cql_order_specification_visitor=None,
                       sql_order_specification_visitor=None,
                       eval_order_specification_visitor=None,
                       url_converter=None,
                       **kw):
        # Set default values for options.
        if filter_specification_factory is None:
            filter_specification_factory = FilterSpecificationFactory()
        if order_specification_factory is None:
            order_specification_factory = OrderSpecificationFactory()
        if service is None:
            service = Service()
        if cql_filter_specification_visitor is None:
            cql_filter_specification_visitor = CqlFilterSpecificationVisitor
        if sql_filter_specification_visitor is None:
            sql_filter_specification_visitor = SqlFilterSpecificationVisitor
        if eval_filter_specification_visitor is None:
            eval_filter_specification_visitor = \
                                    ObjectFilterSpecificationVisitor
        if cql_order_specification_visitor is None:
            cql_order_specification_visitor = CqlOrderSpecificationVisitor
        if sql_order_specification_visitor is None:
            sql_order_specification_visitor = SqlOrderSpecificationVisitor
        if eval_order_specification_visitor is None:
            eval_order_specification_visitor = ObjectOrderSpecificationVisitor
        if url_converter is None:
            url_converter = ResourceUrlConverter
        PyramidConfigurator.setup_registry(self, **kw)
        self.__setup_everest(
               filter_specification_factory=filter_specification_factory,
               order_specification_factory=order_specification_factory,
               service=service,
               cql_filter_specification_visitor=
                                    cql_filter_specification_visitor,
               sql_filter_specification_visitor=
                                    sql_filter_specification_visitor,
               eval_filter_specification_visitor=
                                    eval_filter_specification_visitor,
               cql_order_specification_visitor=
                                    cql_order_specification_visitor,
               sql_order_specification_visitor=
                                    sql_order_specification_visitor,
               eval_order_specification_visitor=
                                    eval_order_specification_visitor,
               url_converter=url_converter)

    def add_repository(self, name, repository_type, repository_class,
                       aggregate_class, make_default, configuration):
        """
        Generic method for adding a repository.
        """
        repo_mgr = self.get_registered_utility(IRepositoryManager)
        if name is None:
            # If no name was given, this is assumed to be the ROOT repository
            # for the given repository type.
            name = REPOSITORY_DOMAINS.ROOT
        repo = repo_mgr.new(repository_type, name=name,
                            make_default=make_default,
                            repository_class=repository_class,
                            aggregate_class=aggregate_class,
                            configuration=configuration)
        repo_mgr.set(repo)

    def add_rdb_repository(self, name=None, repository_class=None,
                           aggregate_class=None,
                           make_default=False, configuration=None, _info=u''):
        if configuration is None:
            configuration = {}
        setting_info = [('db_string', 'db_string')]
        configuration.update(
                        self.get_configuration_from_settings(setting_info))
        self.add_repository(name, REPOSITORY_TYPES.RDB, repository_class,
                            aggregate_class, make_default, configuration)

    def add_filesystem_repository(self, name=None, repository_class=None,
                                  aggregate_class=None,
                                  make_default=False, configuration=None,
                                  _info=u''):
        if configuration is None:
            configuration = {}
        setting_info = [('directory', 'fs_directory'),
                        ('content_type', 'fs_contenttype')]
        configuration.update(
                        self.get_configuration_from_settings(setting_info))
        self.add_repository(name, REPOSITORY_TYPES.FILE_SYSTEM,
                            repository_class, aggregate_class,
                            make_default, configuration)

    def add_memory_repository(self, name=None, repository_class=None,
                              aggregate_class=None,
                              make_default=False, configuration=None,
                              _info=u''):
        if configuration is None:
            configuration = {}
        self.add_repository(name, REPOSITORY_TYPES.MEMORY, repository_class,
                            aggregate_class, make_default, configuration)

    def setup_system_repository(self, repository_type, reset_on_start=False):
        repo_mgr = self.get_registered_utility(IRepositoryManager)
        # We have to pass the repository class explicitly as the repo
        # manager can not use the registry (yet).
        repo_cls = self.get_registered_utility(IRepository,
                                               name=repository_type)
        repo_mgr.setup_system_repository(repository_type, reset_on_start,
                                         repository_class=repo_cls)
        self.add_resource(IUserMessage, UserMessageMember, UserMessage,
                          repository=REPOSITORY_DOMAINS.SYSTEM,
                          collection_root_name='_messages')
        self.registry.registerUtility(UserMessageNotifier(), # pylint:disable=E1103
                                      IUserMessageNotifier)

    def add_resource(self, interface, member, entity,
                     collection=None,
                     collection_root_name=None, collection_title=None,
                     expose=True, repository=None, _info=u''):
        if not IInterface in provided_by(interface):
            raise ValueError('The interface argument must be an Interface.')
        if not (isinstance(member, type)
                and IMemberResource in provided_by(object.__new__(member))):
            raise ValueError('The member argument must be a class that '
                             'implements IMemberResource.')
        if member.relation is None:
            raise ValueError('The member class must have a "relation" '
                             'attribute.')
        if not (isinstance(entity, type)
                and IEntity in provided_by(object.__new__(entity))):
            raise ValueError('The entity argument must be a class that '
                             'implements IEntity.')
        # Configure or create the collection class.
        if collection is None:
            collection = type('%sCollection' % member.__name__,
                              (Collection,), {})
            if collection_title is None:
                collection.title = 'Collection of %s' % member.__name__
        elif not issubclass(collection, Collection):
            raise ValueError('The collection class must be a subclass '
                             'of Collection.')
        # Configure the specified repository.
        repo_mgr = self.get_registered_utility(IRepositoryManager)
        if repository is None:
            repo = repo_mgr.get_default()
        else:
            repo = repo_mgr.get(repository)
            if repo is None:
                # Add a root repository with default configuration on
                # the fly.
                repo_type = getattr(REPOSITORY_TYPES, repository, None)
                if repo_type is None:
                    raise ValueError('Unknown repository type "%s".'
                                     % repository)
                if repo_type == REPOSITORY_TYPES.RDB:
                    self.add_rdb_repository(name=REPOSITORY_TYPES.RDB)
                elif repo_type == REPOSITORY_TYPES.FILE_SYSTEM:
                    self.add_filesystem_repository(
                                            name=REPOSITORY_TYPES.FILE_SYSTEM)
                else:
                    raise NotImplementedError()
                repo = repo_mgr.get(repository)
        # Override the root name and title the collection, if requested.
        if not collection_root_name is None:
            collection.root_name = collection_root_name
        if not collection_title is None:
            collection.title = collection_title
        if collection.relation is None:
            collection.relation = '%s-collection' % member.relation
        if expose and collection.root_name is None:
            # Check that we have a root collection name *before* we register
            # all the adapters and utilities.
            raise ValueError('To expose a collection resource in the '
                             'service (=root), a root name is required.')
        # Register the entity instance -> member instance adapter.
        mb_factory = member.create_from_entity
        self._register_adapter(mb_factory, (interface,), IMemberResource,
                               info=_info)
        # Register adapter object implementing instance -> member class
        self._register_adapter(lambda obj: member,
                               required=(interface,),
                               provided=IMemberResource,
                               name='member-class',
                               info=_info)
        # Register adapter object implementing instance -> collection class
        self._register_adapter(lambda obj: collection,
                               required=(interface,),
                               provided=ICollectionResource,
                               name='collection-class',
                               info=_info)
        # Register adapter object implementing instance -> entity class
        self._register_adapter(lambda obj: entity,
                               required=(interface,),
                               provided=IEntity,
                               name='entity-class',
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
        # Attach the marker interface to the registered resource classes, if
        # necessary, so the instances will provide it.
        if not interface in provided_by(member):
            class_implements(member, interface)
        if not interface in provided_by(collection):
            class_implements(collection, interface)
        if not interface in provided_by(entity):
            class_implements(entity, interface)
        # This enables us to pass a class instead of
        # an interface or instance to the various adapters.
        also_provides(member, interface)
        also_provides(collection, interface)
        also_provides(entity, interface)
        # Register utility member relation -> member class
        self._register_utility(member, IRelation,
                               name=member.relation)
        # Register utility collection relation -> collection class
        self._register_utility(collection, IRelation,
                               name=collection.relation)
        # Register the resource with the repository.
        repo.register_resource(collection)
        # Register adapter implementing interface -> repository.
        self._register_adapter(lambda obj: repo,
                               required=(interface,),
                               provided=IRepository,
                               info=_info)
        # Install an attribute injector in the entity class. This will, on
        # first access, replace the __everest_attributes__ class attribute
        # with an ordered dictionary mapping entity attribute names to
        # resource descriptors.
        entity.__everest_attributes__ = resource_attributes_injector()
        # Expose (=register with the service) if requested.
        if expose:
            srvc = self.query_registered_utilities(IService)
            srvc.register(interface)

    def add_representer(self, content_type=None, representer_class=None,
                        options=None, _info=u''):
        if content_type is None and representer_class is None:
            raise ValueError('Either content type or representer class must '
                             'be provided.')
        if not content_type is None and not representer_class is None:
            raise ValueError('Either content type or representer class may '
                             'be provided, but not both.')
        if options is None:
            options = {}
        rpr_reg = self.get_registered_utility(IRepresenterRegistry)
        if not representer_class is None:
            rpr_reg.register_representer_class(representer_class)
            if issubclass(representer_class, MappingResourceRepresenter):
                mp_reg = rpr_reg.get_mapping_registry(
                                            representer_class.content_type)
            else: # pragma: no cover
                # FIXME: This is for representers that bypass the mapping
                #        machinery by using custom parsers/generators. Needs
                #        a test case.
                mp_reg = None
        else:
            mp_reg = rpr_reg.get_mapping_registry(content_type)
        if not mp_reg is None:
            for name, value in iteritems_(options):
                mp_reg.set_default_config_option(name, value)

    def add_resource_representer(self, resource, content_type,
                                 options=None, attribute_options=None,
                                 _info=u''):
        if IInterface in provided_by(resource):
            # If we got an interface, we register representers with the same
            # configuration for the registered member and collection resources.
            rcs = [self.get_registered_utility(resource,
                                               name='member-class'),
                   self.get_registered_utility(resource,
                                               name='collection-class')]
        else:
            if not issubclass(resource, Resource):
                raise ValueError('Representers can only be registered for '
                                 'classes inheriting from the Resource base '
                                 'class.')
            rcs = [resource]
        rpr_reg = self.get_registered_utility(IRepresenterRegistry)
        mp_reg = rpr_reg.get_mapping_registry(content_type)
        rpr_config = \
                mp_reg.configuration_class(options=options,
                                           attribute_options=attribute_options)
        for rc in rcs:
            rpr_reg.register(rc, content_type, configuration=rpr_config)

    def add_resource_view(self, resource, view=None, name='', renderer=None,
                          request_method=(RequestMethods.GET,),
                          default_content_type=None,
                          default_response_content_type=None,
                          enable_messaging=None, **kw):
        # FIXME: We should not allow **kw to support setting up standard
        #        views here since some options may have undesired side
        #        effects.
        if isinstance(request_method, string_types):
            request_method = (request_method,)
        if IInterface in provided_by(resource):
            if not view is None:
                raise ValueError('Must pass a resource class, not an '
                                 'interface, when a custom view is '
                                 'specified.')
            rcs = [self._get_utility(resource, 'collection-class'),
                   self._get_utility(resource, 'member-class')]
        else:
            rcs = [resource]
        for rc in rcs:
            self.__add_resource_view(rc, view, name, renderer, request_method,
                                     default_content_type,
                                     default_response_content_type,
                                     enable_messaging, kw)

    def add_collection_view(self, resource, **kw):
        if IInterface in provided_by(resource):
            resource = self._get_utility(resource, 'collection-class')
        self.add_resource_view(resource, **kw)

    def add_member_view(self, resource, **kw):
        if IInterface in provided_by(resource):
            resource = self._get_utility(resource, 'member-class')
        self.add_resource_view(resource, **kw)

    @action_method
    def add_renderer(self, name, factory):
        # Pyramid has default renderers (e.g., for JSON) that conflict with
        # the everest renderers, hence we override add_renderer to only add
        # the non-conflicting
        if not (name in get_registered_representer_names()
                and factory is not RendererFactory):
            PyramidConfigurator.add_renderer(self, name, factory)

    def _get_utility(self, *args, **kw):
        return self.registry.getUtility(*args, **kw) # pylint: disable=E1103

    def _register_utility(self, *args, **kw):
        return self.registry.registerUtility(*args, **kw) # pylint: disable=E1103

    def _register_adapter(self, *args, **kw):
        return self.registry.registerAdapter(*args, **kw) # pylint: disable=E1103

    def _set_filter_specification_factory(self, filter_specification_factory):
        self._register_utility(filter_specification_factory,
                               IFilterSpecificationFactory)

    def _set_order_specification_factory(self, order_specification_factory):
        self._register_utility(order_specification_factory,
                               IOrderSpecificationFactory)

    def _set_service(self, service):
        self._register_utility(service, IService)

    def _set_cql_filter_specification_visitor(self,
                                           cql_filter_specification_visitor):
        self._register_utility(cql_filter_specification_visitor,
                               IFilterSpecificationVisitor,
                              name=EXPRESSION_KINDS.CQL)

    def _set_sql_filter_specification_visitor(self,
                                           sql_filter_specification_visitor):
        self._register_utility(sql_filter_specification_visitor,
                               IFilterSpecificationVisitor,
                               name=EXPRESSION_KINDS.SQL)

    def _set_eval_filter_specification_visitor(self,
                                           eval_filter_specification_visitor):
        self._register_utility(eval_filter_specification_visitor,
                               IFilterSpecificationVisitor,
                               name=EXPRESSION_KINDS.EVAL)

    def _set_cql_order_specification_visitor(self,
                                             cql_order_specification_visitor):
        self._register_utility(cql_order_specification_visitor,
                               IOrderSpecificationVisitor,
                               name=EXPRESSION_KINDS.CQL)

    def _set_sql_order_specification_visitor(self,
                                             sql_order_specification_visitor):
        self._register_utility(sql_order_specification_visitor,
                               IOrderSpecificationVisitor,
                               name=EXPRESSION_KINDS.SQL)

    def _set_eval_order_specification_visitor(self,
                                             eval_order_specification_visitor):
        self._register_utility(eval_order_specification_visitor,
                               IOrderSpecificationVisitor,
                               name=EXPRESSION_KINDS.EVAL)

    def _set_url_converter(self, url_converter):
        self._register_adapter(url_converter, (IRequest,),
                               IResourceUrlConverter)

    def __setup_everest(self,
                filter_specification_factory,
                order_specification_factory,
                service,
                cql_filter_specification_visitor,
                sql_filter_specification_visitor,
                eval_filter_specification_visitor,
                cql_order_specification_visitor,
                sql_order_specification_visitor,
                eval_order_specification_visitor,
                url_converter):
        # These are core initializations which should only be done once.
        if self.query_registered_utilities(IRepositoryManager) is None:
            # Set up the repository class utilities.
            mem_repo_class = self.query_registered_utilities(
                                    IRepository, name=REPOSITORY_TYPES.MEMORY)
            if mem_repo_class is None:
                self._register_utility(MemoryRepository, IRepository,
                                       name=REPOSITORY_TYPES.MEMORY)
                mem_repo_class = MemoryRepository
            if self.query_registered_utilities(
                    IRepository, name=REPOSITORY_TYPES.FILE_SYSTEM) is None:
                self._register_utility(FileSystemRepository, IRepository,
                                       name=REPOSITORY_TYPES.FILE_SYSTEM)
            if self.query_registered_utilities(
                    IRepository, name=REPOSITORY_TYPES.RDB) is None:
                self._register_utility(RdbRepository, IRepository,
                                       name=REPOSITORY_TYPES.RDB)
            # Set up the repository manager.
            repo_mgr = RepositoryManager()
            self._register_utility(repo_mgr, IRepositoryManager)
            self.add_subscriber(repo_mgr.on_app_created, IApplicationCreated)
            # Set up the root MEMORY repository and set it as the default
            # for all resources that do not specify a repository.
            self.add_repository(REPOSITORY_DOMAINS.ROOT,
                                REPOSITORY_TYPES.MEMORY,
                                mem_repo_class, None, True, None)
            # Create representer registry and register builtin
            # representer classes.
            rpr_reg = RepresenterRegistry()
            rpr_reg.register_representer_class(CsvResourceRepresenter)
            rpr_reg.register_representer_class(JsonResourceRepresenter)
            rpr_reg.register_representer_class(XmlResourceRepresenter)
            rpr_reg.register_representer_class(AtomResourceRepresenter)
            self._register_utility(rpr_reg, IRepresenterRegistry)
        # Register renderer factories for registered representers.
        for reg_rnd_name in get_registered_representer_names():
            rnd = self.query_registered_utilities(IRendererFactory,
                                                  reg_rnd_name)
            if not isinstance(rnd, RendererFactory):
                PyramidConfigurator.add_renderer(self, reg_rnd_name,
                                                 RendererFactory)
        # Register data traversal proxy factory and adapters.
        trv_prx_fac = DataTraversalProxyFactory()
        self._register_utility(trv_prx_fac, IDataTraversalProxyFactory)
        self._register_adapter(DomainDataTraversalProxyAdapter,
                               (IEntity,),
                               IDataTraversalProxyAdapter)
        self._register_adapter(DataElementDataTraversalProxyAdapter,
                               (IMemberDataElement,),
                               IDataTraversalProxyAdapter)
        self._register_adapter(DataElementDataTraversalProxyAdapter,
                               (ICollectionDataElement,),
                               IDataTraversalProxyAdapter)
        self._register_adapter(LinkedDomainDataTraversalProxyAdapter,
                               (ILinkedDataElement,),
                               IDataTraversalProxyAdapter)
        #
        if not filter_specification_factory is None:
            self._set_filter_specification_factory(
                                                filter_specification_factory)
        if not order_specification_factory is None:
            self._set_order_specification_factory(order_specification_factory)
        if not service is None:
            self._set_service(service)
        if not cql_filter_specification_visitor is None:
            self._set_cql_filter_specification_visitor(
                                            cql_filter_specification_visitor)
        if not sql_filter_specification_visitor is None:
            self._set_sql_filter_specification_visitor(
                                            sql_filter_specification_visitor)
        if not eval_filter_specification_visitor is None:
            self._set_eval_filter_specification_visitor(
                                            eval_filter_specification_visitor)
        if not cql_order_specification_visitor is None:
            self._set_cql_order_specification_visitor(
                                            cql_order_specification_visitor)
        if not sql_order_specification_visitor is None:
            self._set_sql_order_specification_visitor(
                                            sql_order_specification_visitor)
        if not eval_order_specification_visitor is None:
            self._set_eval_order_specification_visitor(
                                            eval_order_specification_visitor)
        if not url_converter is None:
            self._set_url_converter(url_converter)

    def __add_resource_view(self, rc, view, name, renderer, request_methods,
                            default_content_type,
                            default_response_content_type,
                            enable_messaging, options):
        for request_method in request_methods:
            opts = options.copy()
            vw = view
            if vw is None \
               or (isinstance(view, type) and
                   issubclass(view, RepresentingResourceView)):
                register_sub_views = name == ''
                kw = dict(default_content_type=default_content_type,
                          default_response_content_type=
                                    default_response_content_type,
                          enable_messaging=enable_messaging,
                          convert_response=renderer is None)
                if view is None:
                    # Attempt to guess a default view. We register a factory
                    # so we can pass additional constructor arguments.
                    if provides_member_resource(rc):
                        if request_method == RequestMethods.GET:
                            vw = self.__make_view_factory(GetMemberView, kw)
                        elif request_method == RequestMethods.PUT:
                            vw = self.__make_view_factory(PutMemberView, kw)
                        elif request_method == RequestMethods.PATCH:
                            vw = self.__make_view_factory(PatchMemberView, kw)
                        elif request_method == RequestMethods.DELETE:
                            # The DELETE view is special as it does not have
                            # to deal with representations.
                            vw = DeleteMemberView
                            register_sub_views = False
                        elif request_method == RequestMethods.FAKE_PUT:
                            request_method = RequestMethods.POST
                            opts['header'] = 'X-HTTP-Method-Override:PUT'
                            vw = self.__make_view_factory(PutMemberView, kw)
                        elif request_method == RequestMethods.FAKE_PATCH:
                            request_method = RequestMethods.POST
                            opts['header'] = 'X-HTTP-Method-Override:PATCH'
                            vw = self.__make_view_factory(PatchMemberView, kw)
                        elif request_method == RequestMethods.FAKE_DELETE:
                            request_method = RequestMethods.POST
                            opts['header'] = 'X-HTTP-Method-Override:DELETE'
                            vw = DeleteMemberView
                            register_sub_views = False
                        else:
                            mb_req_methods = [rm for rm in RequestMethods
                                              if not rm == 'POST']
                            raise ValueError('Autodetection for member '
                                             'resource views requires '
                                             'one of %s as request method.'
                                             % str(mb_req_methods))
                    else:
                        if request_method == RequestMethods.GET:
                            vw = \
                              self.__make_view_factory(GetCollectionView, kw)
                        elif request_method == RequestMethods.POST:
                            vw = \
                              self.__make_view_factory(PostCollectionView, kw)
                        else:
                            coll_req_methods = [RequestMethods.GET,
                                                RequestMethods.POST]
                            raise ValueError('Autodetection for collectioon '
                                             'resource views requires '
                                             'one of %s as request method.'
                                             % str(coll_req_methods))
                else:
                    vw = self.__make_view_factory(view, kw)
            else:
                register_sub_views = False
            vnames = set([name])
            if register_sub_views:
                # Add sub-views for registered representer names if this view
                # uses representers (and is not a named view itself).
                vnames.update(get_registered_representer_names())
            for vname in vnames:
                self.add_view(context=rc, view=vw, renderer=renderer,
                              request_method=request_method, name=vname,
                              **opts)

    def __make_view_factory(self, view_class, kw):
        def view_factory(context, request):
            return view_class(context, request, **kw)()
        return view_factory

