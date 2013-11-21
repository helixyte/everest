"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 21, 2013.
"""
from everest.representers.base import MappingResourceRepresenter
from everest.resources.base import Resource

__docformat__ = 'reStructuredText en'
__all__ = ['RepresenterRegistry',
           ]


class RepresenterRegistry(object):
    """
    Registry for representer classes and representer factories.

    For representers deriving from :class:`MappingResourceRepresenter`, a
    mapping registry is created which then can be retrieved using the
    :method:`get_mapping_registry` method.
    """
    def __init__(self):
        self.__rpr_classes = {}
        self.__mp_regs = {}
        self.__rpr_factories = {}

    def register_representer_class(self, representer_class):
        """
        Registers the given representer class with this registry, using
        its MIME content type as the key.
        """
        if representer_class in self.__rpr_classes.values():
            raise ValueError('The representer class "%s" has already been '
                             'registered.' % representer_class)
        self.__rpr_classes[representer_class.content_type] = representer_class
        if issubclass(representer_class, MappingResourceRepresenter):
            # Create and hold a mapping registry for the registered resource
            # representer class.
            mp_reg = representer_class.make_mapping_registry()
            self.__mp_regs[representer_class.content_type] = mp_reg

    def is_registered_representer_class(self, representer_class):
        """
        Checks if the given representer class has been registered with this
        registry.

        :returns: Boolean check result.
        """
        return representer_class in self.__rpr_classes.values()

    def get_mapping_registry(self, content_type):
        """
        Returns the mapping registry for the given MIME content type.

        :param content_type: registered MIME content type (see
          :class:`everest.mime.MimeTypeRegistry`).
        :returns: instance of :class:`everest.mapping.MappingRegistry`.
        """
        return self.__mp_regs.get(content_type)

    def register(self, resource_class, content_type, configuration=None):
        """
        Registers a representer factory for the given combination of resource
        class and content type.

        :param configuration: representer configuration. A default instance
          will be created if this is not given.
        :type configuration:
            :class:`everest.representers.config.RepresenterConfiguration`
        """
        if not issubclass(resource_class, Resource):
            raise ValueError('Representers can only be registered for '
                             'resource classes (got: %s).' % resource_class)
        if not content_type in self.__rpr_classes:
            raise ValueError('No representer class has been registered for '
                             'content type "%s".' % content_type)
        # Register a factory resource -> representer for the given combination
        # of resource class and content type.
        rpr_cls = self.__rpr_classes[content_type]
        self.__rpr_factories[(resource_class, content_type)] = \
                                            rpr_cls.create_from_resource_class
        if issubclass(rpr_cls, MappingResourceRepresenter):
            # Create or update an attribute mapping.
            mp_reg = self.__mp_regs[content_type]
            mp = mp_reg.find_mapping(resource_class)
            if mp is None:
                # No mapping was registered yet for this resource class or any
                # of its base classes; create a new one on the fly.
                new_mp = mp_reg.create_mapping(resource_class, configuration)
            elif not configuration is None:
                if resource_class is mp.mapped_class:
                    # We have additional configuration for an existing mapping.
                    mp.configuration.update(configuration)
                    new_mp = mp
                else:
                    # We have a derived class with additional configuration.
                    new_mp = mp_reg.create_mapping(
                                            resource_class,
                                            configuration=mp.configuration)
                    new_mp.configuration.update(configuration)
            elif not resource_class is mp.mapped_class:
                # We have a derived class without additional configuration.
                new_mp = mp_reg.create_mapping(resource_class,
                                               configuration=mp.configuration)
            else:
                # We found a dynamically created mapping for the right class
                # without additional configuration; do not create a new one.
                new_mp = None
            if not new_mp is None:
                # Store the new (or updated) mapping.
                mp_reg.set_mapping(new_mp)

    def create(self, resource_class, content_type):
        """
        Creates a representer for the given combination of resource and
        content type. This will also find representer factories that were
        registered for a base class of the given resource.
        """
        rpr_fac = self.__find_representer_factory(resource_class,
                                                  content_type)
        if rpr_fac is None:
            # Register a representer with default configuration on the fly
            # and look again.
            self.register(resource_class, content_type)
            rpr_fac = self.__find_representer_factory(resource_class,
                                                      content_type)
        return rpr_fac(resource_class)

    def __find_representer_factory(self, resource_class, content_type):
        rpr_fac = None
        for base_rc_cls in resource_class.__mro__:
            try:
                rpr_fac = self.__rpr_factories[(base_rc_cls, content_type)]
            except KeyError:
                pass
            else:
                break
        return rpr_fac


