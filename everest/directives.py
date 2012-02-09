"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 16, 2011.
"""

from everest.configuration import Configurator
from repoze.bfg.threadlocal import get_current_registry
from repoze.bfg.zcml import IViewDirective
from repoze.bfg.zcml import view as bfg_view
from zope.configuration.fields import Bool # pylint: disable=E0611,F0401
from zope.configuration.fields import GlobalObject # pylint: disable=E0611,F0401
from zope.configuration.fields import Path # pylint: disable=E0611,F0401
from zope.configuration.fields import Tokens # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.interface.interfaces import IInterface  # pylint: disable=E0611,F0401
from zope.schema import TextLine # pylint: disable=E0611,F0401
from everest.resources.interfaces import IPersister
from everest.resources.persisters import PERSISTER_TYPES
from everest.resources.persisters import FileSystemPersister
from everest.resources.persisters import OrmPersister
from everest.resources.interfaces import IDefaultPersister

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

class IPersisterDirective(Interface):
    name = \
        TextLine(title=u"Name of this persister. Must be unique among all "
                        "persisters. If no name is given, or the name is "
                        "specified as 'DEFAULT', the built-in persister is "
                        "configured with the given directive.",
                 required=False
                 )
    make_default = \
        Bool(title=u"Indicates if this persister should be made the default "
                    "for all resources that do not explicitly specify a "
                    "persister. Defaults to False.",
             required=False
             )


def _persister(_context, name, make_default, prst_type, cnf):
    # Persister directives are applied eagerly. Note that custom persisters 
    # must be declared *before* they can be referenced in resource directives.
    reg = get_current_registry()
    config = Configurator(reg, package=_context.package)
    if name is None:
        # Configuration for the built-in persister.
        prst = config.get_registered_utility(IPersister, prst_type)
        prst.configure(**cnf) # pylint: disable=W0142
        if make_default:
            # Replace builtin default persister.
            reg.registerUtility(prst, IDefaultPersister) # pylint: disable=E1103
    else:
        if prst_type == PERSISTER_TYPES.FILE_SYSTEM:
            prst_cls = FileSystemPersister
        elif prst_type == PERSISTER_TYPES.ORM:
            prst_cls = OrmPersister
        else:
            raise ValueError('Unknown persister type "%s".' % prst_type)
        config.add_persister(name, prst_cls,
                             make_default=make_default, configuration=cnf)
    discriminator = (prst_type, name)
    _context.action(discriminator=discriminator)


class IFileSystemPersisterDirective(IPersisterDirective):
    directory = \
        Path(title=u"The directory the representation files for the "
                    "root collection resources are kept. Defaults to "
                    "the current working directory.",
             required=False,
             )
    content_type = \
        GlobalObject(title=u"The (MIME) content type to use for the "
                            "representation files. Defaults to CSV.",
                     required=False)


def fs_persister(_context, name=None, make_default=False, directory=None,
                 content_type=None):
    """
    Directive for registering a file-system based persister.
    """
    cnf = {}
    if not directory is None:
        cnf['directory'] = directory
    if not content_type is None:
        cnf['content_type'] = content_type
    _persister(_context, name, make_default, PERSISTER_TYPES.FILE_SYSTEM, cnf)


class IOrmPersisterDirective(IPersisterDirective):
    db_string = \
        TextLine(title=u"String to use to connect to the DB server. Defaults "
                        "to an in-memory sqlite DB.",
                 required=False)
    metadata_factory = \
        GlobalObject(title=u"Callback that initializes and returns the "
                            "metadata for the ORM.",
                     required=False)


def orm_persister(_context, name=None, make_default=False, db_string=None,
                  metadata_factory=None):
    """
    Directive for registering an ORM based persister.
    """
    cnf = {}
    if not db_string is None:
        cnf['db_string'] = db_string
    if not metadata_factory is None:
        cnf['metadata_factory'] = metadata_factory
    _persister(_context, name, make_default, PERSISTER_TYPES.ORM, cnf)


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
    persister = \
        TextLine(title=u"The name of the persister that should be used for "
                        "this resource. Defaults to 'DUMMY', the built-in "
                        "dummy persister (i.e., no persistence); see the "
                        "IPersisterDirective for other possible values.",
                 required=False)
    expose = \
        Bool(title=u"Flag indicating if this collection should be exposed in "
                    "the service.",
             default=True,
             required=False,
             )
#    request_methods = \
#        Tokens(title=u"HTTP request methods supported by this resource.",
#               value_type=Choice(values=['GET', 'POST', 'DELETE']),
#               default='GET',
#               )


def resource(_context, interface, member, entity,
             collection=None, aggregate=None,
             entity_adapter=None, aggregate_adapter=None,
             collection_root_name=None, collection_title=None,
             persister=None, expose=True):
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
                        persister=persister,
                        expose=expose,
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
        if IInterface in provided_by(rc):
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
        if IInterface in provided_by(rc):
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
