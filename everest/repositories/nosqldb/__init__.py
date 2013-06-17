"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 11, 2013.
"""
from .aggregate import NoSqlRootAggregate as Aggregate
try:
    from .repository import NoSqlRepository as Repository
except ImportError:
    # We do not have support for MongoDB.
    pass
