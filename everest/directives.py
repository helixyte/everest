"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 16, 2011.
"""

from everest.configuration import Configurator
from everest.repository import REPOSITORIES
from pyramid.threadlocal import get_current_registry
from pyramid_zcml import IViewDirective
from pyramid_zcml import view as pyramid_view
from zope.configuration.config import GroupingContextDecorator # pylint: disable=E0611,F0401
from zope.configuration.config import IConfigurationContext # pylint: disable=E0611,F0401
from zope.configuration.fields import Bool # pylint: disable=E0611,F0401
from zope.configuration.fields import GlobalObject # pylint: disable=E0611,F0401
from zope.configuration.fields import Path # pylint: disable=E0611,F0401
from zope.configuration.fields import Tokens # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401
from zope.interface import implements # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.interface.interfaces import IInterface  # pylint: disable=E0611,F0401
from zope.schema import TextLine # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['ICollectionViewDirective',
           'IFileSystemRepositoryDirective',
           'IMemberViewDirective',
           'IMemoryRepositoryDirective',
           'IOrmRepositoryDirective',
           'IRepresenterDirective',
           'IResourceDirective',
           'collection_view',
           'filesystem_repository',
           'member_view',
           'memory_repository',
           'orm_repository',
           'representer',
           'resource',
           ]


# interfaces to not have an __init__ # pylint: disable=W0232

class IRepositoryDirective(Interface):
    name = \
        TextLine(title=u"Name of this repository. Must be unique among all "
                        "repositories. If no name is given, or the name is "
                        "specified as 'DEFAULT', the built-in repository is "
                        "configured with the given directive.",
                 required=False
                 )
    aggregate_class = \
        GlobalObject(title=u"A class to use as the default aggregate "
                            "implementation for this repository.",
                     required=False)
    make_default = \
        Bool(title=u"Indicates if this repository should be made the default "
                    "for all resources that do not explicitly specify a "
                    "repository. Defaults to False.",
             required=False
             )


def _repository(_context, name, make_default, agg_cls,
                repo_type, config_method, cnf):
    # Repository directives are applied eagerly. Note that custom repositories 
    # must be declared *before* they can be referenced in resource directives.
    discriminator = (repo_type, name)
    _context.action(discriminator=discriminator)
    reg = get_current_registry()
    config = Configurator(reg, package=_context.package)
    method = getattr(config, config_method)
    if name is None: # re-configure builtin repository.
        name = repo_type
    method(name, aggregate_class=agg_cls,
           configuration=cnf, make_default=make_default)


class IMemoryRepositoryDirective(IRepositoryDirective):
    pass


def memory_repository(_context, name=None, make_default=False,
                      aggregate_class=None):
    _repository(_context, name, make_default,
                aggregate_class,
                REPOSITORIES.MEMORY, 'add_memory_repository', {})


class IFileSystemRepositoryDirective(IRepositoryDirective):
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


def filesystem_repository(_context, name=None, make_default=False,
                          aggregate_class=None,
                          directory=None, content_type=None):
    """
    Directive for registering a file-system based repository.
    """
    cnf = {}
    if not directory is None:
        cnf['directory'] = directory
    if not content_type is None:
        cnf['content_type'] = content_type
    _repository(_context, name, make_default,
                aggregate_class,
                REPOSITORIES.FILE_SYSTEM, 'add_filesystem_repository', cnf)


class IOrmRepositoryDirective(IRepositoryDirective):
    db_string = \
        TextLine(title=u"String to use to connect to the DB server. Defaults "
                        "to an in-memory sqlite DB.",
                 required=False)
    metadata_factory = \
        GlobalObject(title=u"Callback that initializes and returns the "
                            "metadata for the ORM.",
                     required=False)


def orm_repository(_context, name=None, make_default=False,
                   aggregate_class=None,
                   db_string=None,
                   metadata_factory=None):
    """
    Directive for registering an ORM based repository.
    """
    cnf = {}
    if not db_string is None:
        cnf['db_string'] = db_string
    if not metadata_factory is None:
        cnf['metadata_factory'] = metadata_factory
    _repository(_context, name, make_default,
                aggregate_class,
                REPOSITORIES.ORM, 'add_orm_repository', cnf)


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
    repository = \
        TextLine(title=u"The name of the repository that should be used for "
                        "this resource. Defaults to 'MEMORY', the built-in "
                        "in-memory repository (i.e., no persistence); see "
                        "the IRepositoryDirective for other possible values.",
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
             collection=None, collection_root_name=None, collection_title=None,
             repository=None, expose=True):
    """
    Directive for registering a resource. Calls
    :method:`everest.configuration.Configurator.add_resource`.
    """
    # Register resources eagerly so the various adapters and utilities are
    # available for other directives.
    discriminator = ('resource', interface)
    _context.action(discriminator=discriminator)
    reg = get_current_registry()
    config = Configurator(reg, package=_context.package)
    config.add_resource(interface, member, entity,
                        collection=collection,
                        collection_root_name=collection_root_name,
                        collection_title=collection_title,
                        repository=repository,
                        expose=expose,
                        _info=_context.info)


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
        pyramid_view(_context, context=rc, **kw)


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
        pyramid_view(_context, context=rc, **kw)


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
        GlobalObject(title=u"Old-style configuration class for this "
                            "representer.",
                     required=False)


class RepresenterDirective(GroupingContextDecorator):
    """
    Grouping directive for registering a representer for a given resource(s) 
    and content type combination. Delegates the work to a
    :class:`everest.configuration.Configurator`.
    """
    implements(IConfigurationContext, IRepresenterDirective)

    def __init__(self, context, for_, content_type, configuration=None):
        self.context = context
        self.for_ = for_
        self.content_type = content_type
        self.configuration = configuration
        self.options = {}
        self.mapping_info = {}

    def after(self):
        reg = get_current_registry()
        config = Configurator(reg, package=self.context.package)
        mapping_info = \
            None if len(self.mapping_info) == 0 else self.mapping_info
        for rc in self.for_:
            discriminator = ('representer', rc, self.content_type)
            self.action(discriminator=discriminator, # pylint: disable=E1101
                        callable=config.add_representer,
                        args=(rc, self.content_type),
                        kw=dict(configuration=self.configuration,
                                mapping_info=mapping_info,
                                _info=self.context.info))


class IRepresenterAttributeDirective(Interface):
    name = \
        TextLine(title=u"Name of the representer attribute.")


class RepresenterAttributeDirective(GroupingContextDecorator):
    implements(IConfigurationContext, IRepresenterAttributeDirective)

    def __init__(self, context, name):
        self.context = context
        self.name = name
        self.options = {}

    def after(self):
        self.context.mapping_info[self.name] = self.options


class IOptionDirective(Interface):
    name = \
        TextLine(title=u"Name of the option.")
    value = \
        TextLine(title=u"Value of the option.")
    type = \
        GlobalObject(title=u"Type of the option. This is only needed if the "
                            "option value needs to be something else than a "
                            "string; should be a Zope configuration field "
                            "type such as zope.configuration.fields.Bool.",
                     required=False)


def option(_context, name, value, type=None): # pylint: disable=W0622
    grouping_context = _context.context
    if not type is None:
        field = type()
        value = field.fromUnicode(value)
    grouping_context.options[name] = value

# pylint: enable=W0232
