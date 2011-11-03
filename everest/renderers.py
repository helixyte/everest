"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created Oct 7, 2011.
"""

from everest.mime import ATOM_ENTRY_MIME
from everest.mime import ATOM_FEED_MIME
from everest.mime import ATOM_MIME
from everest.mime import ATOM_SERVICE_MIME
from everest.mime import CsvMime
from everest.representers.utils import as_representer
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IResource
from everest.resources.interfaces import IService
from everest.url import resource_to_url
from repoze.bfg.chameleon_zpt import ZPTTemplateRenderer
from repoze.bfg.chameleon_zpt import get_template
from repoze.bfg.interfaces import IRenderer
from repoze.bfg.renderers import template_renderer_factory
from repoze.bfg.url import model_url
from repoze.bfg.url import static_url
from rfc3339 import rfc3339
from zope.interface import implements # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401

__docformat__ = "reStructuredText en"
__all__ = ['atom_template_renderer_factory',
           'csv_renderer_factory'
           ]


def atom_template_renderer_factory(path):
    return template_renderer_factory(path, AtomTemplateRenderer)


def renderer_factory(name):
    if name == 'csv':
        renderer = CsvRenderer()
    elif name == 'atom':
        renderer = AtomRenderer()
    else:
        raise ValueError('Unknown renderer name "%s"' % name)
    return renderer


# FIXME: Retire this when all templates have been replaced. #pylint: disable=W0511
class AtomTemplateRenderer(ZPTTemplateRenderer):
    """
    """

    FEED_MASTER = 'templates/feed/master.atom'
    ENTRY_MASTER = 'templates/entry/master.atom'

    def __init__(self, path):
        ZPTTemplateRenderer.__init__(self, path)

    def __call__(self, value, system):
        context = value.get('context', system['context'])
        request = system['request']
        provided = provided_by(context)
        if IMemberResource in provided:
            mime = ATOM_ENTRY_MIME
            system['master'] = get_template(self.ENTRY_MASTER)
        elif ICollectionResource in provided:
            mime = ATOM_FEED_MIME
            system['master'] = get_template(self.FEED_MASTER)
        elif IService in provided:
            mime = ATOM_SERVICE_MIME
        else:
            raise ValueError('Context is not an IResource')
        request.response_content_type = mime
        if context.cache_for is not None:
            request.response_cache_for = context.cache_for
        #system['unitconv'] = unitconv
        system['static_url'] = static_url
        system['model_url'] = model_url
        system['rfc3339'] = rfc3339
        system['resource_to_url'] = resource_to_url
        return ZPTTemplateRenderer.__call__(self, value, system)


class ResourceRenderer(object):
    implements(IRenderer)

    def __init__(self, format): # redef format pylint:disable=W0622
        self._format = format

    def __call__(self, value, system):
        context = value.get('context', system.get('context'))
        if not IResource in provided_by(context):
            raise ValueError('Context is not a resource.')
        if not self._validate(context):
            raise ValueError('Invalid representation.')
        self._prepare_response(system)
        # Assemble response.
        rpr = as_representer(context, self._format)
        return rpr.to_string(context)

    def _validate(self, value):
        raise NotImplementedError('Abstract method.')

    def _prepare_response(self, system):
        raise NotImplementedError('Abstract method.')


class AtomRenderer(ResourceRenderer):

    def __init__(self):
        ResourceRenderer.__init__(self, ATOM_MIME)

    def _validate(self, value):
        return IResource in  provided_by(value)

    def _prepare_response(self, system):
        request = system['request']
        request.response_content_type = self._format
        context = system['context']
        if context.cache_for is not None:
            request.response_cache_for = context.cache_for


class CsvRenderer(ResourceRenderer):

    def __init__(self):
        ResourceRenderer.__init__(self, CsvMime.mime_string)

    def _validate(self, resource):
        return IResource in provided_by(resource)

    def _prepare_response(self, system):
        # Set up response type.
        request = system['request']
        request.response_content_type = self._format
        context = system['context']
        if ICollectionResource in provided_by(context):
            # Disable batching for CSV rendering.
            context.slice = None
