"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

The entity repository class.

Created on Jan 11, 2012.
"""

from everest.entities.interfaces import IAggregateImplementationRegistry
from everest.entities.interfaces import IEntityRepository
from everest.entities.interfaces import IStagingContextManager
from everest.entities.utils import get_aggregate_class
from everest.entities.utils import get_entity_class
from everest.repository import Repository
from repoze.bfg.threadlocal import get_current_registry
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401
from zope.interface import implements # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['AggregateImplementationRegistry',
           'EntityRepository',
           'StagingContextManager',
           ]


class AggregateImplementationRegistry(object):
    """
    Registry for aggregate implementation classes.
    
    Each registered class may define an initialization callback which is 
    
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
    implements(IEntityRepository)

    def __init__(self, implementation_registry=None):
        Repository.__init__(self)
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
        with the implementation resitry (e.g., using the 
        :meth:`register_implementation` method.
        
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
        implementation resitry (e.g., using the :meth:`register_implementation`
        method.
        
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

    def _make_key(self, rc):
        return get_aggregate_class(rc)

    def _make_new(self, rc):
        agg_cls = get_aggregate_class(rc)
        entity_cls = get_entity_class(rc)
        if not issubclass(agg_cls,
                          tuple(self.__impl_registry.get_registered())):
            # If no custom agg class implementation was registered, we use
            # the default implementation (either explicitly set or the
            # generic default).
            impl_cls = self.__impls.get(agg_cls) \
                       or self.__default_impl
            impl = impl_cls(entity_cls)
            agg = agg_cls.create(entity_cls, impl)
        else:
            agg = agg_cls.create(entity_cls)
        return agg

    def __check_impl(self, implementation_class):
        if not self.__impl_registry.is_registered(implementation_class):
            raise ValueError('You must register the implementation class '
                             'before you can use it.')


class StagingContextManager(object):
    """
    Staging context manager.
    
    Provides a context for the entity repository ensuring that all dynamically
    created aggregates use a particular implementation.
    """
    implements(IStagingContextManager)

    def __init__(self, aggregate_implementation):
        self.__new_agg_impl = aggregate_implementation
        self.__original_ent_repo = None

    def __enter__(self):
        reg = get_current_registry()
        self.__original_ent_repo = reg.getUtility(IEntityRepository)
        new_ent_repo = EntityRepository()
        new_ent_repo.set_default_implementation(self.__new_agg_impl)
        reg.registerUtility(new_ent_repo, IEntityRepository)
        return new_ent_repo

    def __exit__(self, exc_type, value, tb):
        reg = get_current_registry()
        reg.registerUtility(self.__original_ent_repo, IEntityRepository)
