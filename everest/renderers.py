"""
Renderers.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created Oct 7, 2011.
"""
from pyramid.interfaces import IRenderer

from everest.mime import AtomMime
from everest.mime import CsvMime
from everest.mime import JsonMime
from everest.mime import XmlMime
from everest.representers.utils import as_representer
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IResource
from zope.interface import implementer # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401


__docformat__ = "reStructuredText en"
__all__ = ['AtomRenderer',
           'CsvRenderer',
           'JsonRenderer',
           'RendererFactory',
           'ResourceRenderer',
           'XmlRenderer',
           ]


class RendererFactory(object):
    """
    Factory for renderers based on names.
    """
    def __init__(self, info):
        self.__name = info.name

    def __call__(self, value, system):
        if self.__name == 'csv':
            rnd = CsvRenderer()
        elif self.__name == 'json':
            rnd = JsonRenderer()
        elif self.__name == 'xml':
            rnd = XmlRenderer()
        elif self.__name == 'atom':
            rnd = AtomRenderer()
        else:
            raise ValueError('Unknown renderer name "%s"' % self.__name)
        return rnd(value, system)


@implementer(IRenderer)
class ResourceRenderer(object):
    """
    Renderer for resources.

    Uses a representer to perform the resource -> representation conversion.
    """
    def __init__(self, content_type): # redef format pylint:disable=W0622
        self._content_type = content_type

    def __call__(self, value, system):
        context = value.get('context', system.get('context'))
        if not self._validate(context):
            raise ValueError('Invalid representation.')
        self._prepare_response(system)
        # Assemble response.
        rpr = as_representer(context, self._content_type)
        return rpr.to_bytes(context)

    @property
    def _format(self):
        return self._content_type.mime_type_string

    def _validate(self, value):
        return IResource in  provided_by(value)

    def _prepare_response(self, system):
        # Set up response type.
        rsp = system['request'].response
        rsp.content_type = self._format


class CsvRenderer(ResourceRenderer):
    """
    Renderer creating a CSV representation from a resource.
    """
    def __init__(self):
        ResourceRenderer.__init__(self, CsvMime)

    def _prepare_response(self, system):
        ResourceRenderer._prepare_response(self, system)
        context = system['context']
        if ICollectionResource in provided_by(context):
            # Disable batching for CSV rendering.
            context.slice = None


class JsonRenderer(ResourceRenderer):
    """
    Renderer creating a JSON representation from a resource.
    """
    def __init__(self):
        ResourceRenderer.__init__(self, JsonMime)


class XmlRenderer(ResourceRenderer):
    """
    Renderer creating a XML representation from a resource.
    """
    def __init__(self):
        ResourceRenderer.__init__(self, XmlMime)


class AtomRenderer(ResourceRenderer):
    """
    Renderer creating an ATOM representation from a resource.
    """
    def __init__(self):
        ResourceRenderer.__init__(self, AtomMime)
