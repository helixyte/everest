"""
Custom resource object tree traverser.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 4, 2011.
"""
from everest.resources.interfaces import IResource
from pyramid.traversal import ResourceTreeTraverser

__docformat__ = 'reStructuredText en'
__all__ = ['SuffixResourceTraverser',
           ]


class SuffixResourceTraverser(ResourceTreeTraverser):
    """
    A custom resource tree traverser that allows us to specify the
    representation for resources with a suffix as in
    `http://everest/myobjects.csv`.

    Rather than to reproduce the functionality of the `__call__` method, we
    check if base part of the current view name (`myobjects` in the example)
    can be retrieved as a child resource from the context. If yes, we set the
    context to the resource and the view name to the extension part of the
    current view name (`csv` in the example); if no, nothing is changed.
    """
    def __call__(self, request):
        system = ResourceTreeTraverser.__call__(self, request)
        context = system['context']
        view_name = system['view_name']
        if IResource.providedBy(context) and '.' in view_name: # pylint: disable=E1101
            rc_name, repr_name = view_name.split('.')
            try:
                child_rc = context[rc_name]
            except KeyError:
                pass
            else:
                if IResource.providedBy(child_rc): # pylint: disable=E1101
                    system['context'] = child_rc
                    system['view_name'] = repr_name
        return system
