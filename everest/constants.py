"""
Constants.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Mar 29, 2013.
"""
from pyramid.compat import PY3

__docformat__ = 'reStructuredText en'
__all__ = ['CARDINALITIES',
           'CARDINALITY_CONSTANTS',
           'Cardinality',
           'DEFAULT_CASCADE',
           'MAPPING_DIRECTIONS',
           'RELATIONSHIP_DIRECTIONS',
           'RELATION_OPERATIONS',
           'DEFAULT_CASCADE',
           'RESOURCE_ATTRIBUTE_KINDS',
           'RESOURCE_KINDS',
           ]


class MetaConstantGroup(type):
    """
    Meta class that makes constant group classes iterable.
    """
    def __iter__(mcs):
        for key in mcs.__dict__.keys():
            if not key.startswith('_'):
                yield key

if PY3: # pragma: no cover
    # PY3 compatible way of using the metaclass (__metaclass__ does not work)
    # that keeps pylint happy (no syntax error under Python 2.x).
    ConstantGroup = MetaConstantGroup('ConstantGroup', (object,), {})
else: # pragma: no cover
    class ConstantGroup(object):
        __metaclass__ = MetaConstantGroup

# Assigning __doc__ outside __init__ pylint: disable=W0201
ConstantGroup.__doc__ = \
"""
Base class for all constant group classes.

To use, declare the individual values of a constant group in the class
namespace: ::

class MyConstGroup(ConstantGroup):
    FOO = 'Foo'
    BAR = 'Bar'

You can then iterate over the constants (`for const in MyConstGroup:`)
or get a list of all constants in the group (`list(MyConstGroup)`).
"""
# pylint: enable=W0201


class RESOURCE_KINDS(ConstantGroup):
    """
    Static container for resource kind constants.

    We have two kinds of resource:
        MEMBER :
            a member resource
        COLLECTION :
            a collection resource
    """
    MEMBER = 'MEMBER'
    COLLECTION = 'COLLECTION'


class RESOURCE_ATTRIBUTE_KINDS(ConstantGroup):
    """
    Static container for resource attribute kind constants.

    We have three kinds of resource attribute:
        MEMBER :
            a member attribute
        COLLECTION :
            a collection attribute
        TERMINAL :
            an attribute that is not a resource
    """
    MEMBER = RESOURCE_KINDS.MEMBER
    COLLECTION = RESOURCE_KINDS.COLLECTION
    TERMINAL = 'TERMINAL'


class Cardinality(tuple):
    """
    Value object describing the cardinality on both ends of a relationship.

    :ivar relator: cardinality for the relator (source of the relationship).
    :ivar relatee: cardinality for the relatee (target of the relationship).
    """
    def __new__(self, relator, relatee):
        if not set((relator, relatee)).issubset((CARDINALITY_CONSTANTS.ONE,
                                                 CARDINALITY_CONSTANTS.MANY)):
            raise ValueError('"relator" and "relatee" parameters in '
                             'cardinality descriptors must be "%s" or '
                             '"%s".' % (CARDINALITY_CONSTANTS.ONE,
                                        CARDINALITY_CONSTANTS.MANY))
        new_obj = tuple.__new__(self, (relator, relatee))
        new_obj.relator = relator
        new_obj.relatee = relatee
        return new_obj

    def __str__(self):
        return '%s->%s' % \
         (self.relator if self.relator == CARDINALITY_CONSTANTS.ONE else '*',
          self.relatee if self.relatee == CARDINALITY_CONSTANTS.ONE else '*')


class CARDINALITY_CONSTANTS(ConstantGroup):
    """
    Constants for cardinality values.
    """
    ONE = 'ONE'
    MANY = 'MANY'


class CARDINALITIES(ConstantGroup):
    """
    Relationship cardinality constants for non-terminal resource attributes.
    """
    ONETOONE = Cardinality(CARDINALITY_CONSTANTS.ONE,
                           CARDINALITY_CONSTANTS.ONE)
    ONETOMANY = Cardinality(CARDINALITY_CONSTANTS.ONE,
                            CARDINALITY_CONSTANTS.MANY)
    MANYTOONE = Cardinality(CARDINALITY_CONSTANTS.MANY,
                            CARDINALITY_CONSTANTS.ONE)
    MANYTOMANY = Cardinality(CARDINALITY_CONSTANTS.MANY,
                             CARDINALITY_CONSTANTS.MANY)


class RELATION_OPERATIONS(ConstantGroup):
    """
    Constants for relation operations.
    """
    ADD = 1
    REMOVE = 2
    UPDATE = 4

    @staticmethod
    def check(source, target):
        return RELATION_OPERATIONS.ADD if target is None \
               else RELATION_OPERATIONS.REMOVE if source is None \
               else RELATION_OPERATIONS.UPDATE


#: The cascade chains enabled by default are "save-update" and "merge"
DEFAULT_CASCADE = RELATION_OPERATIONS.ADD | RELATION_OPERATIONS.UPDATE


class RELATIONSHIP_DIRECTIONS(ConstantGroup):
    """
    Constants specifying the direction of a relationship.
    """
    NONE = 0
    FORWARD = 1
    REVERSE = 2
    BIDIRECTIONAL = 3


class MAPPING_DIRECTIONS(ConstantGroup):
    """
    Constants specifying the direction resource data are mapped.
    """
    #: Resource data are being read (i.e., a representation is converted
    #: to a resource.
    READ = 'READ'
    #: Resource data are being written (i.e., a resource is converted
    #: to a representation.
    WRITE = 'WRITE'


class RequestMethods(ConstantGroup):
    """
    Request methods supported by everest.
    """
    GET = 'GET'
    PUT = 'PUT'
    PATCH = 'PATCH'
    POST = 'POST'
    DELETE = 'DELETE'
    FAKE_PUT = 'FAKE_PUT'
    FAKE_PATCH = 'FAKE_PATCH'
    FAKE_DELETE = 'FAKE_DELETE'


class ResourceReferenceRepresentationKinds(ConstantGroup):
    """
    Kinds of resource reference representations.
    """
    OFF = 'OFF'
    INLINE = 'INLINE'
    URL = 'URL'
