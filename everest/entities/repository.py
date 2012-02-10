"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

The entity repository class.

Created on Jan 11, 2012.
"""

from everest.entities.interfaces import IAggregateImplementationRegistry
from everest.entities.utils import get_aggregate_class
from everest.entities.utils import get_entity_class
from everest.repository import Repository
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401
from zope.interface import implements # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['AggregateImplementationRegistry',
           'EntityRepository',
           ]


class AggregateImplementationRegistry(object):
    """
    Registry for aggregate implementation classes.
    """
    implements(IAggregateImplementationRegistry)

    def __init__(self):
        self.__registry = set()

    def register(self, implementation_class):
        self.__registry.add(implementation_class)

    def unregister(self, implementation_classs):
        self.__registry.remove(implementation_classs)

    def is_registered(self, implementation_class):
        return implementation_class in self.__registry

    def get_registered(self):
        return self.__registry.copy()


class EntityRepository(Repository):
    """
    The entity repository manages entity accessors (aggregates).
    
    In addition to creating and caching aggregates, the entity repository
    also provides facilities to interact with the aggregate implementation
    registry. This makes it possible to switch the implementation used for 
    freshly created aggregates at runtime.
    """
    def __init__(self, persister, implementation_registry=None):
        Repository.__init__(self)
        #
        self.__persister = persister
        #
        if implementation_registry is None:
            implementation_registry = \
                                get_utility(IAggregateImplementationRegistry)
        self.__impl_registry = implementation_registry
        # The implementation map (keys are resource interfaces, values 
        # aggregate implementations).
        self.__impls = {}
        #  The default aggregate implementation class.
        self.__default_impl = None

    def register_implementation(self, implementation_class,
                                make_default=False):
        """
        Convenience method for registering an aggregate implementation with
        the registry.
        
        :param implementation_class: aggregate implementation class to
          register.
        :param init_callback: initialization callback (accepts settings
          parameter and returns None)
        """
        self.__impl_registry.register(implementation_class)
        if make_default:
            self.set_default_implementation(implementation_class)

    def set_implementation(self, rc, implementation_class):
        """
        Sets the implementation to use for the specified resource interface.
        Note that the given implementation class has to be registered before
        with the implementation registry (e.g., using the 
        :meth:`register_implementation` method).
        
        The next time :meth:`get` is called, a fresh aggregates will be created
        that uses the new implementation class.
        """
        self.__check_impl(implementation_class)
        agg_cls = get_aggregate_class(rc)
        self.clear(agg_cls)
        self.__impls[agg_cls] = implementation_class

    def set_default_implementation(self, implementation_class):
        """
        Sets the default implementation for all resource interfaces. Note that 
        the given implementation class has to be registered before with the
        implementation registry (e.g., using the :meth:`register_implementation`
        method).
        
        All future aggregates obtained through the :meth:`get` method will use 
        the new implementation class.
        """
        self.__check_impl(implementation_class)
        self.clear_all()
        self.__default_impl = implementation_class

    def get_default_implementation(self):
        """
        Returns the default implementation for all resource interfaces.
        """
        return self.__default_impl

    def new(self, rc):
        agg_cls = get_aggregate_class(rc)
        entity_cls = get_entity_class(rc)
        if not issubclass(agg_cls,
                          tuple(self.__impl_registry.get_registered())):
            # Typcical case - "normal" Aggregate class.
            impl_cls = self.__impls.get(agg_cls) or self.__default_impl
            impl = impl_cls.create(entity_cls, self.__persister.session)
            agg = agg_cls.create(impl)
        else:
            # Special case - customized AggregateImpl class.
            agg = agg_cls.create(entity_cls, self.__persister.session)
        return agg

    def configure(self, **config):
        self.__persister.configure(**config)

    def initialize(self):
        self.__persister.initialize()

    @property
    def is_initialized(self):
        return self.__persister.is_initialized

    def _make_key(self, rc):
        return get_aggregate_class(rc)

    def __check_impl(self, implementation_class):
        if not self.__impl_registry.is_registered(implementation_class):
            raise ValueError('You must register the implementation class '
                             'before you can use it.')
