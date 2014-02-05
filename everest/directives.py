"""
ZCML directives for everest.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 16, 2011.
"""
from pyramid.compat import iteritems_
from pyramid.threadlocal import get_current_registry
from pyramid_zcml import IViewDirective

from everest.configuration import Configurator
from everest.constants import RESOURCE_KINDS
from everest.constants import RequestMethods
from everest.repositories.constants import REPOSITORY_TYPES
from everest.representers.config import IGNORE_OPTION
from everest.representers.config import WRITE_AS_LINK_OPTION
from everest.representers.config import WRITE_MEMBERS_AS_LINK_OPTION
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_member_class
from zope.configuration.config import GroupingContextDecorator # pylint: disable=E0611,F0401
from zope.configuration.config import IConfigurationContext # pylint: disable=E0611,F0401
from zope.configuration.fields import Bool # pylint: disable=E0611,F0401
from zope.configuration.fields import GlobalObject # pylint: disable=E0611,F0401
from zope.configuration.fields import Path # pylint: disable=E0611,F0401
from zope.configuration.fields import Tokens # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401
from zope.interface import implementer # pylint: disable=E0611,F0401
from zope.schema import Choice # pylint: disable=E0611,F0401
from zope.schema import TextLine # pylint: disable=E0611,F0401
from everest.constants import ResourceReferenceRepresentationKinds

__docformat__ = 'reStructuredText en'
__all__ = ['IFileSystemRepositoryDirective',
           'IMemoryRepositoryDirective',
           'IMessagingDirective',
           'IOptionDirective',
           'IRdbRepositoryDirective',
           'IRepositoryDirective',
           'IRepresenterDirective',
           'IResourceDirective',
           'IResourceRepresenterAttributeDirective',
           'IRepresenterDirective',
           'RepresenterDirective',
           'ResourceDirective',
           'ResourceRepresenterAttributeDirective',
           'ResourceRepresenterDirective',
           'collection_view',
           'filesystem_repository',
           'member_view',
           'memory_repository',
           'messaging',
           'option',
           'rdb_repository',
           'resource_view',
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
    repository_class = \
        GlobalObject(title=u"A class to use as the implementation for this "
                            "repository.",
                     required=False)
    make_default = \
        Bool(title=u"Indicates if this repository should be made the default "
                    "for all resources that do not explicitly specify a "
                    "repository. Defaults to False.",
             required=False
             )


def _repository(_context, name, make_default, agg_cls, repo_cls,
                repo_type, config_method, cnf):
    # Repository directives are applied eagerly. Note that custom repositories
    # must be declared *before* they can be referenced in resource directives.
    discriminator = (repo_type, name)
    _context.action(discriminator=discriminator)
    reg = get_current_registry()
    config = Configurator(reg, package=_context.package)
    method = getattr(config, config_method)
    method(name, aggregate_class=agg_cls, repository_class=repo_cls,
           configuration=cnf, make_default=make_default)


class IMemoryRepositoryDirective(IRepositoryDirective):
    cache_loader = \
        GlobalObject(title=u"A callable that accepts an entity class and "
                            "returns a sequence of entity instances which "
                            "will be used to populate the cache on startup.",
                     required=False)


def memory_repository(_context, name=None, make_default=False,
                      aggregate_class=None, repository_class=None,
                      cache_loader=None):
    cnf = {}
    if not cache_loader is None:
        cnf['cache_loader'] = cache_loader
    _repository(_context, name, make_default,
                aggregate_class, repository_class,
                REPOSITORY_TYPES.MEMORY, 'add_memory_repository', cnf)


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
                          aggregate_class=None, repository_class=None,
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
                aggregate_class, repository_class,
                REPOSITORY_TYPES.FILE_SYSTEM, 'add_filesystem_repository',
                cnf)


class IRdbRepositoryDirective(IRepositoryDirective):
    db_string = \
        TextLine(title=u"String to use to connect to the DB server. Defaults "
                        "to an in-memory sqlite DB.",
                 required=False)
    metadata_factory = \
        GlobalObject(title=u"Callback that initializes and returns the "
                            "metadata for the DB.",
                     required=False)


def rdb_repository(_context, name=None, make_default=False,
                   aggregate_class=None, repository_class=None,
                   db_string=None, metadata_factory=None):
    """
    Directive for registering a RDBM based repository.
    """
    cnf = {}
    if not db_string is None:
        cnf['db_string'] = db_string
    if not metadata_factory is None:
        cnf['metadata_factory'] = metadata_factory
    _repository(_context, name, make_default,
                aggregate_class, repository_class,
                REPOSITORY_TYPES.RDB, 'add_rdb_repository', cnf)


class IMessagingDirective(Interface):
    repository = \
        TextLine(title=u"Repository type to use for the system repository.",
                 required=True,
                 )
    reset_on_start = \
        Bool(title=u"Erase all stored system resources on startup. This only "
                    "has an effect in persistent repositories.",
             required=False)


def messaging(_context, repository, reset_on_start=False):
    """
    Directive for setting up the user message resource in the appropriate
    repository.

    :param str repository: The repository to create the user messages resource
      in.
    """
    discriminator = ('messaging', repository)
    reg = get_current_registry()
    config = Configurator(reg, package=_context.package)
    _context.action(discriminator=discriminator, # pylint: disable=E1101
                    callable=config.setup_system_repository,
                    args=(repository,),
                    kw=dict(reset_on_start=reset_on_start))


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


@implementer(IConfigurationContext, IResourceDirective)
class ResourceDirective(GroupingContextDecorator):
    """
    Directive for registering a resource. Calls
    :meth:`everest.configuration.Configurator.add_resource`.
    """
    def __init__(self, context, interface, member, entity,
                 collection=None, collection_root_name=None,
                 collection_title=None, repository=None, expose=True):
        GroupingContextDecorator.__init__(self, context)
        self.context = context
        self.interface = interface
        self.member = member
        self.entity = entity
        self.collection = collection
        self.collection_root_name = collection_root_name
        self.collection_title = collection_title
        self.repository = repository
        self.expose = expose
        self.representers = {}

    def after(self):
        # Register resources eagerly so the various adapters and utilities are
        # available for other directives.
        discriminator = ('resource', self.interface)
        reg = get_current_registry()
        config = Configurator(reg, package=self.context.package)
        config.add_resource(self.interface, self.member, self.entity,
                            collection=self.collection,
                            collection_root_name=self.collection_root_name,
                            collection_title=self.collection_title,
                            repository=self.repository,
                            expose=self.expose,
                            _info=self.context.info)
        for key, value in iteritems_(self.representers):
            cnt_type, rc_kind = key
            opts, mp_opts = value
            if rc_kind == RESOURCE_KINDS.MEMBER:
                rc = get_member_class(self.interface)
            elif rc_kind == RESOURCE_KINDS.COLLECTION:
                rc = get_collection_class(self.interface)
            else: # None
                rc = self.interface
            discriminator = ('resource_representer', rc, cnt_type, rc_kind)
            self.action(discriminator=discriminator, # pylint: disable=E1101
                        callable=config.add_resource_representer,
                        args=(rc, cnt_type),
                        kw=dict(options=opts,
                                attribute_options=mp_opts,
                                _info=self.context.info),
                        )


def _resource_view(_context, for_, default_content_type,
                   default_response_content_type, enable_messaging,
                   config_callable_name, kw):
    reg = get_current_registry()
    config = Configurator(reg, package=_context.package)
    config_callable = getattr(config, config_callable_name)
    option_tuples = tuple(sorted([(k, str(v)) for (k, v) in kw.items()]))
    kw['default_content_type'] = default_content_type
    kw['default_response_content_type'] = default_response_content_type
    kw['enable_messaging'] = enable_messaging
    for rc in for_:
        discriminator = ('resource_view', rc, config_callable_name) \
                        + option_tuples
        _context.action(discriminator=discriminator, # pylint: disable=E1101
                        callable=config_callable,
                        args=(rc,),
                        kw=kw)


class IResourceViewDirective(IViewDirective):
    for_ = \
        Tokens(title=u"The resource classes or interfaces to set up views "
                      "for. For each interface in the sequence, views for "
                      "the associated member resource class (member_view), "
                      "the associated collection resource class "
                      "(collection_view) or both (resource_view) are"
                      "generated.",
               required=True,
               value_type=GlobalObject())
    default_content_type = \
        GlobalObject(title=u"The default MIME content type to use when the "
                            "client does not indicate a preference. Unless "
                            "the default_response_content_type setting is "
                            "also specified, this applies to both the "
                            "request and the response content type.",
                     required=False)
    default_response_content_type = \
        GlobalObject(title=u"The default MIME content type to use for the "
                            "response when the client does not indicate a "
                            "preference. If this is not specified, the "
                            "setting for default_content_type is used.",
                     required=False)
    request_method = \
        Tokens(title=u"One or more request methods that need to be matched.",
               required=True,
               value_type=Choice(values=tuple(RequestMethods),
                                 default=RequestMethods.GET,
                                 ),
               )
    enable_messaging = \
        Bool(title=u"Flag indicating if messaging should be enabled for "
                    "this view (defaults to False for GET views and to "
                    "TRUE for PUT/POST/PATCH views).",
             default=None,
             required=False,
             )


def resource_view(_context, for_, default_content_type=None,
                  default_response_content_type=None, enable_messaging=None,
                  **kw):
    _resource_view(_context, for_, default_content_type,
                   default_response_content_type, enable_messaging,
                   'add_resource_view', kw)


def collection_view(_context, for_, default_content_type=None,
                    default_response_content_type=None,
                    enable_messaging=None, **kw):
    _resource_view(_context, for_, default_content_type,
                   default_response_content_type, enable_messaging,
                   'add_collection_view', kw)


def member_view(_context, for_, default_content_type=None,
                default_response_content_type=None, enable_messaging=None,
             **kw):
    _resource_view(_context, for_, default_content_type,
                   default_response_content_type, enable_messaging,
                   'add_member_view', kw)


class IRepresenterDirective(Interface):
    content_type = \
        GlobalObject(title=u"The (MIME) content type for the representer "
                            "to configure. If this is given, the "
                            "'representer_class' option must not be given.",
                     required=False)
    representer_class = \
        GlobalObject(title=u"Class to use for the representer.  If this is "
                            "given, the 'content_type' option must not be "
                            "given.",
                     required=False)


@implementer(IConfigurationContext, IRepresenterDirective)
class RepresenterDirective(GroupingContextDecorator):
    def __init__(self, context, content_type=None, representer_class=None):
        GroupingContextDecorator.__init__(self, context)
        self.context = context
        self.content_type = content_type
        self.representer_class = representer_class
        self.options = {}

    def after(self):
        discriminator = \
            ('representer',
             self.content_type or self.representer_class.content_type)
        self.action(discriminator=discriminator) # pylint: disable=E1101
        # Representers are created eagerly so the resource declarations can use
        # them.
        reg = get_current_registry()
        config = Configurator(reg, package=self.context.package)
        config.add_representer(content_type=self.content_type,
                               representer_class=self.representer_class,
                               options=self.options)


class IResourceRepresenterDirective(Interface):
    content_type = \
        GlobalObject(title=u"The (MIME) content type the representer manages.",
                     required=True)
    kind = \
        Choice(values=(RESOURCE_KINDS.MEMBER.lower(),
                       RESOURCE_KINDS.COLLECTION.lower()),
               title=u"Specifies the kind of resource the representer should "
                      "be used for ('member' or 'collection'). If this is "
                      "not provided, the representer is used for both "
                      "resource kinds.",
               required=False)


@implementer(IConfigurationContext, IResourceRepresenterDirective)
class ResourceRepresenterDirective(GroupingContextDecorator):
    """
    Grouping directive for registering a representer for a given resource(s)
    and content type combination. Delegates the work to a
    :class:`everest.configuration.Configurator`.
    """

    def __init__(self, context, content_type, kind=None):
        GroupingContextDecorator.__init__(self, context)
        self.context = context
        self.content_type = content_type
        if not kind is None:
            kind = kind.upper()
        self.kind = kind
        self.options = {}
        self.attribute_options = {}

    def after(self):
        attribute_options = None if len(self.attribute_options) == 0 \
                            else self.attribute_options
        options = self.options
        self.context.representers[(self.content_type, self.kind)] = \
                                                (options, attribute_options)


class IResourceRepresenterAttributeDirective(Interface):
    name = \
        TextLine(title=u"Name of the representer attribute.")


@implementer(IConfigurationContext, IResourceRepresenterAttributeDirective)
class ResourceRepresenterAttributeDirective(GroupingContextDecorator):
    def __init__(self, context, name):
        GroupingContextDecorator.__init__(self, context)
        self.context = context
        self.name = name
        self.options = {}

    def after(self):
        # Convert the (nested) attribute names into keys.
        key = tuple(self.name.split('.'))
        self.context.attribute_options[key] = self.options


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
    elif name in (IGNORE_OPTION, WRITE_AS_LINK_OPTION,
                  WRITE_MEMBERS_AS_LINK_OPTION):
        field = Bool()
        value = field.fromUnicode(value)
    grouping_context.options[name] = value


class IRefDirective(Interface):
    attribute = TextLine(title=u"The resource attribute the link is "
                                "referencing.")
    kind = Choice(title=u"The kind of resource reference representation to "
                         "use.",
                  values=tuple(ResourceReferenceRepresentationKinds))


def ref(_context, attribute, kind):
    grouping_context = _context.context
    options = dict()
    if kind == ResourceReferenceRepresentationKinds.INLINE:
        options[IGNORE_OPTION] = False
        options[WRITE_AS_LINK_OPTION] = False
    elif kind == ResourceReferenceRepresentationKinds.URL:
        options[IGNORE_OPTION] = False
        options[WRITE_AS_LINK_OPTION] = True
    else:
        options[IGNORE_OPTION] = True
    key = tuple(attribute.split('.'))
    grouping_context.attribute_options[key] = options


# pylint: enable=W0232
