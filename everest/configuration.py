"""
This file is part of the everest project. 
See LICENSE.txt for licensing, AUTHORS.txt for contributor information.

Created on Jun 22, 2011.
"""

from everest.entities.base import Aggregate
from everest.entities.base import Entity
from everest.entities.interfaces import IAggregate
from everest.entities.interfaces import IEntity
from everest.representers.interfaces import IDataElementRegistry
from everest.representers.interfaces import IRepresenter
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.base import Resource
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from repoze.bfg.configuration import Configurator as BfgConfigurator
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

    def add_resource(self, interface, member, entity,
                     collection=None, aggregate=None,
                     entity_adapter=None, aggregate_adapter=None,
                     collection_root_name=None, collection_title=None,
                     _info=u''):
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
            if collection_root_name is None:
                raise ValueError('If no collection class is specified, the '
                                 'collection root name must be provided.')
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
        elif not issubclass(aggregate, Aggregate):
            raise ValueError('The entity aggregate must be a subclass '
                             'of Aggregate.')
        # Override the root name and title the collection, if requested.
        if not collection_root_name is None:
            collection.root_name = collection_root_name
        if not collection_title is None:
            collection.title = collection_title
        # Find interfaces the given classes are required to implement.
#        coll_i_cls = self.__find_interface(collection, IResource)
#        mb_i_cls = self.__find_interface(member, IResource)
#        agg_i_cls = self.__find_interface(aggregate, IEntity)
#        ent_i_cls = self.__find_interface(entity, IEntity)
        register_adapter = self.registry.registerAdapter # pylint: disable=E1103
        register_utility = self.registry.registerUtility # pylint: disable=E1103
        # Register the collection -> member class adapter.
        register_adapter(lambda coll: member,
                                      (interface,), IMemberResource,
                                      name='member-class',
                                      info=_info)
        # Register the member -> collection class adapter.
        register_adapter(lambda member: collection,
                                      (interface,), ICollectionResource,
                                      name='collection-class',
                                      info=_info)
        # Register the collection -> aggregate class adapter.
        register_adapter(lambda coll: aggregate,
                                      (interface,), IAggregate,
                                      info=_info)
        # Register the member -> entity class utility.
        register_adapter(lambda member: entity,
                                      (interface,), IEntity,
                                      info=_info)
        # Register the entity -> member resource adapter.
        if entity_adapter is None:
            mb_factory = member.create_from_entity
        else:
            mb_factory = entity_adapter
        register_adapter(mb_factory, (interface,), IMemberResource,
                                      info=_info)
        # Register the aggregate -> collection resource adapter.
        if aggregate_adapter is None:
            agg_factory = collection.create_from_aggregate
        else:
            agg_factory = aggregate_adapter
        register_adapter(agg_factory, (interface,), ICollectionResource,
                         info=_info)
        # Register utility collection -> collection class
        register_utility(collection, interface, name='collection-class',
                         info=_info)
        # Register utility member -> member class
        register_utility(member, interface, name='member-class',
                         info=_info)
        #
        class_implements(member, interface)
        class_implements(collection, interface)
        class_implements(entity, interface)
        class_implements(aggregate, interface)
        # This enables us to pass the collection  or member class instead of
        # an interface or instance to the various adapters.
        directly_provides(member, interface)
        directly_provides(collection, interface)

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
