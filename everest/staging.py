"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Sep 19, 2011.
"""

from everest.entities.interfaces import IRelationAggregateImplementation
from everest.entities.interfaces import IRootAggregateImplementation
from everest.interfaces import IStagingContextManager
from repoze.bfg.threadlocal import get_current_registry
from zope.interface import implements # pylint: disable=E0611,F0401
import threading

__docformat__ = 'reStructuredText en'
__all__ = ['STAGING_CONTEXT_MANAGERS',
           'StagingContextManagerBase',
           ]


class STAGING_CONTEXT_MANAGERS(object):
    PERSISTENT = 'PERSISTENT'
    TRANSIENT = 'TRANSIENT'


class StagingContextManagerBase(object):
    """
    Base class for staging context managers.
    """
    implements(IStagingContextManager)

    #: The implementation class to use for root aggregates.
    root_aggregate_impl = None
    #: The implementation class to use for relation aggregates.
    relation_aggregate_impl = None

    def __init__(self):
        self.__root_agg_impl = None
        self.__rel_agg_impl = None
        self.__reg_lock = threading.RLock()

    def __enter__(self):
        reg = get_current_registry()
        self.__root_agg_impl = reg.queryUtility(IRootAggregateImplementation)
        self.__rel_agg_impl = reg.queryUtility(IRelationAggregateImplementation)
        with self.__reg_lock:
            if not self.__root_agg_impl is None:
                reg.unregisterUtility(self.__root_agg_impl,
                                      IRootAggregateImplementation)
            if not self.__rel_agg_impl is None:
                reg.unregisterUtility(self.__rel_agg_impl,
                                      IRelationAggregateImplementation)
            reg.registerUtility(self.root_aggregate_impl,
                                IRootAggregateImplementation)
            reg.registerUtility(self.relation_aggregate_impl,
                                IRelationAggregateImplementation)

    def __exit__(self, exc_type, value, tb):
        reg = get_current_registry()
        with self.__reg_lock:
            reg.unregisterUtility(self.root_aggregate_impl,
                                  IRootAggregateImplementation)
            reg.unregisterUtility(self.relation_aggregate_impl,
                                  IRelationAggregateImplementation)
            if not self.__root_agg_impl is None:
                reg.registerUtility(self.__root_agg_impl,
                                    IRootAggregateImplementation)
            if not self.__rel_agg_impl is None:
                reg.registerUtility(self.__rel_agg_impl,
                                    IRelationAggregateImplementation)
