"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created Oct 7, 2011.
"""

from everest.mime import ATOM_MIME
from everest.mime import CsvMime
from everest.representers.utils import as_representer
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IResource
from pyramid.interfaces import IRenderer
from zope.interface import implements # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401

__docformat__ = "reStructuredText en"
__all__ = ['AtomRenderer',
           'CsvRenderer',
           'ResourceRenderer',
           'renderer_factory',
           ]


class RendererFactory(object):
    def __init__(self, info):
        self.__name = info.name

    def __call__(self, value, system):
        if self.__name == 'csv':
            rnd = CsvRenderer()
        elif self.__name == 'atom':
            rnd = AtomRenderer()
        else:
            raise ValueError('Unknown renderer name "%s"' % self.__name)
        return rnd(value, system)


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
        request.response.content_type = self._format
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
        request.response.content_type = self._format
        context = system['context']
        if ICollectionResource in provided_by(context):
            # Disable batching for CSV rendering.
            context.slice = None
