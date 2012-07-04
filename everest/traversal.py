"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 4, 2011.
"""
from everest.resources.interfaces import IResource
from pyramid.traversal import ModelGraphTraverser # pylint: disable-msg=E0611, F0401

__docformat__ = 'reStructuredText en'
__all__ = ['SuffixResourceTraverser',
           ]


class SuffixResourceTraverser(ModelGraphTraverser):
    """
    A custom model traverser that allows us to specify the representation
    for resources with a suffix as in `http://everest/racks.csv`.

    Rather than to reproduce the functionality of the `__call__` method, we
    check if base part of the current view name (`racks` in the example) can
    be retrieved as a child resource from the context. If yes, we set the
    context to the resource and the view name to the extension part of the
    current view name (`csv` in the example); if no, nothing is changed.
    """
    def __call__(self, request):
        system = ModelGraphTraverser.__call__(self, request)
        context = system['context']
        view_name = system['view_name']
        if IResource.providedBy(context) and '.' in view_name: # pylint: disable=E1101
            rc_name, repr_name = view_name.split('.')
            try:
                collection = context[rc_name]
            except KeyError:
                pass
            else:
                if IResource.providedBy(collection): # pylint: disable=E1101
                    system['context'] = collection
                    system['view_name'] = repr_name
        return system
