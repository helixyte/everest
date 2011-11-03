"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 16, 2011.
"""

from everest.configuration import Configurator
from repoze.bfg.threadlocal import get_current_registry
from repoze.bfg.zcml import IViewDirective
from repoze.bfg.zcml import view as bfg_view
from zope.configuration.fields import GlobalObject # pylint: disable=E0611,F0401
from zope.configuration.fields import Tokens # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401
from zope.interface.interfaces import IInterface  # pylint: disable=E0611,F0401
from zope.schema import TextLine # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['ICollectionViewDirective',
           'IMemberViewDirective',
           'IRepresenterDirective',
           'IResourceDirective',
           'collection_view',
           'member_view',
           'representer',
           'resource',
           ]


# interfaces to not have an __init__ # pylint: disable=W0232
class IResourceDirective(Interface):
    interface = \
        GlobalObject(title=u"The marker interface to use for this resource.",
                     required=True,
                     )
    member = \
        GlobalObject(title=u"The member resource class for this resource.",
                     required=True,
                     )
    entity = \
        GlobalObject(title=u"The entity class associated with the member "
                            "resource.",
                     required=True,
                     )
    collection = \
        GlobalObject(title=u"The collection resource class for the member "
                            "resource. If this is not specified, a dynamic "
                            "default class is created using the values of "
                            "`collection_root_name` and `collection_title` "
                            "as root name and title, respectively.",
                     required=False,
                     )
    aggregate = \
        GlobalObject(title=u"The aggregate class associated with the "
                            "entity resource. If this is not specified, "
                            "a dynamic class is created.",
                     required=False,
                     )
    entity_adapter = \
        GlobalObject(title=u"Callable adapting an entity to a member "
                            "resource instance. If this is not specified, "
                            "it defaults to the create_from_entity method "
                            "of the member resource class.",
                     required=False,
                     )
    aggregate_adapter = \
        GlobalObject(title=u"Callable adapting an entity aggregate to a "
                            "collection resource instance. If this is not "
                            "specified, it defaults to the "
                            "create_from_aggregate method of the resource "
                            "class.",
                     required=False,
                     )
    collection_root_name = \
        TextLine(title=u"The name for the root collection (used as URL path "
                        "to the root collection inside the service). Defaults "
                        "to the root_name attribute of the collection class.",
                 required=False,
                 )
    collection_title = \
        TextLine(title=u"The name for the root collection (used as URL path "
                        "to the root collection inside the service). Defaults "
                        "to the root_name attribute of the collection class.",
                 required=False,
                 )
#    expose = \
#        Bool(title=u"Flag indicating if this collection should be exposed in "
#                    "the service (the application root).",
#             default=False,
#             required=False,
#             )
#    request_methods = \
#        Tokens(title=u"HTTP request methods supported by this resource.",
#               value_type=Choice(values=['GET', 'POST', 'DELETE']),
#               default='GET',
#               )


def resource(_context, interface, member, entity,
             collection=None, aggregate=None,
             entity_adapter=None, aggregate_adapter=None,
             collection_root_name=None, collection_title=None):
    """
    Directive for registering a resource. Calls
    :method:`everest.configuration.Configurator.add_resource`.
    """
    # Register resources eagerly so the various adapters and utilities are
    # available for other directives.
    reg = get_current_registry()
    config = Configurator(reg, package=_context.package)
    config.add_resource(interface, member, entity,
                        collection=collection,
                        aggregate=aggregate,
                        entity_adapter=entity_adapter,
                        aggregate_adapter=aggregate_adapter,
                        collection_root_name=collection_root_name,
                        collection_title=collection_title,
                        _info=_context.info)
    discriminator = ('resource', interface)
    _context.action(discriminator=discriminator)


class ICollectionViewDirective(IViewDirective):
    for_ = \
        Tokens(title=u"The collection resource classes or interfaces to use "
                      "this collection resource view with.",
               required=True,
               value_type=GlobalObject())


def collection_view(_context,
                  for_,
                  **kw):
    reg = get_current_registry()
    for rc in for_:
        if IInterface.providedBy(rc):
            rc = reg.getUtility(rc, 'collection-class')
        bfg_view(_context, context=rc, **kw)


class IMemberViewDirective(IViewDirective):
    for_ = \
        Tokens(title=u"The member resource classes or interfaces to use this "
                      "member resource view with.",
               required=True,
               value_type=GlobalObject())


def member_view(_context,
                  for_,
                  **kw):
    reg = get_current_registry()
    for rc in for_:
        if IInterface.providedBy(rc):
            rc = reg.getUtility(rc, 'member-class')
        bfg_view(_context, context=rc, **kw)


class IRepresenterDirective(Interface):
    for_ = \
        Tokens(title=u"The resource classes or interfaces to use this "
                      "representer with.",
               required=True,
               value_type=GlobalObject())
    content_type = \
        GlobalObject(title=u"The (MIME) content type the representer manages.",
                     required=True)
    configuration = \
        GlobalObject(title=u"The configuration map for this representer.",
                     required=False)


def representer(_context, for_, content_type, configuration=None):
    """
    Directive for registering a representer for a given resource(s) and
    content type combination. Delegates the work to a
    :class:`everest.configuration.Configurator`.
    """
    reg = get_current_registry()
    config = Configurator(reg, package=_context.package)
    for rc in for_:
        discriminator = ('representer', rc, content_type)
        _context.action(discriminator=discriminator,
                        callable=config.add_representer,
                        args=(rc, content_type),
                        kw=dict(configuration=configuration,
                                _info=_context.info))

# pylint: enable=W0232
