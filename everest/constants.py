"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Mar 29, 2013.
"""

__docformat__ = 'reStructuredText en'
__all__ = ['CARDINALITIES',
           'CARDINALITY_CONSTANTS',
           'RELATIONSHIP_DIRECTIONS',
           'RELATIONSHIP_OPERATIONS',
           'DEFAULT_CASCADE',
           'RESOURCE_ATTRIBUTE_KINDS',
           'RESOURCE_KINDS',
           ]


class RESOURCE_KINDS(object):
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


class RESOURCE_ATTRIBUTE_KINDS(object):
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


class CARDINALITY_CONSTANTS(object):
    """
    Constants for cardinality values.
    """
    ONE = 'ONE'
    MANY = 'MANY'


class CARDINALITIES(object):
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


class RELATIONSHIP_OPERATIONS(object):
    """
    Constants for relationship operations.
    """
    ADD = 1
    REMOVE = 2
    UPDATE = 4

    @staticmethod
    def check(source, target):
        return RELATIONSHIP_OPERATIONS.ADD if target is None \
               else RELATIONSHIP_OPERATIONS.REMOVE if source is None \
               else RELATIONSHIP_OPERATIONS.UPDATE


#: The cascade chains enabled by default are "save-update" and "merge"
DEFAULT_CASCADE = RELATIONSHIP_OPERATIONS.ADD | RELATIONSHIP_OPERATIONS.UPDATE


class RELATIONSHIP_DIRECTIONS(object):
    NONE = 0
    FORWARD = 1
    REVERSE = 2
    BIDIRECTIONAL = 3
