"""
URL lazy loader.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 25, 2012.
"""
from pyramid.threadlocal import get_current_request
__docformat__ = 'reStructuredText en'
__all__ = ['LazyAttributeLoaderProxy',
           'LazyUrlLoader',
           ]


class LazyUrlLoader(object):
    """
    Helper class for lazy loading of URLs.
    """
    def __init__(self, url, resolver):
        self.__url = url
        self.__resolver = resolver

    def __call__(self):
        request = get_current_request()
        if request is None: # Traversal not yet usable.
            result = None
        else:
            try:
                result = self.__resolver(self.__url)
            except KeyError: # Traversal problem - object not (yet) found.
                result = None
        return result


class LazyAttributeLoaderProxy(object):
    """
    Proxy for lazy loading of attributes referencing entities that are loaded
    through a URL-linked resource.
    """
    def __init__(self, _loader_map=None, **kw):
        if _loader_map is None \
           or not (isinstance(_loader_map, dict) and len(_loader_map) > 0):
            raise ValueError('Must pass _loader_map dictionary containing '
                             'at least one attribute to load lazily.')
        self._loader_map = _loader_map
        super(LazyAttributeLoaderProxy, self).__init__(**kw)

    def __getattribute__(self, attr):
        attrs = object.__getattribute__(self, '__dict__')
        if attr in attrs.get('_loader_map', ()):
            loaded_attrs = self.__load()
            try:
                result = loaded_attrs[attr]
            except KeyError:
                # Loading failed - try again later.
                result = object.__getattribute__(self, attr)
        else:
            result = object.__getattribute__(self, attr)
        return result

    @classmethod
    def create(cls, entity_cls, data):
        """
        Factory class method to create a lazy loader for entities linked 
        through resource URLs.
        
        This returns an instance of a new dynamically created subtype of 
        the given entity class which also inherits from this class to add
        the referenced entity attribute loading functionality. Once all
        referenced entity attributes have been loaded successfully, the
        instance's class is reverted to the given entity class. 
        """
        loader_map = {}
        for attr, value in data.items():
            if isinstance(value, LazyUrlLoader):
                loader_map[attr] = value
                data[attr] = None
        if len(loader_map) > 0:
            data['_loader_map'] = loader_map
            new_type = type('%sLazyAttributeLoaderProxy' % entity_cls.__name__,
                            (cls, entity_cls), {})
            ent = new_type.create_from_data(data)
        else:
            ent = entity_cls.create_from_data(data)
        return ent

    def __load(self):
        loaded_attrs = dict()
        loader_map = object.__getattribute__(self, '_loader_map')
        for attr, loader in loader_map.items():
            # To prevent recursive attempts to load the currently loading
            # attribute, we remove it from the loader map.
            del loader_map[attr]
            resource = loader()
            if resource is None:
                # Resource could not yet be resolved; reinsert for later lazy
                # loading.
                loader_map[attr] = loader
            else:
                new_value = resource.get_entity()
                setattr(self, attr, new_value)
                loaded_attrs[attr] = new_value
        # Once all attributes are loaded successfully, we do not need the
        # proxy any longer.
        if len(loader_map) == 0:
            self.__class__ = self.__class__.__bases__[-1]
            delattr(self, '_loader_map')
        return loaded_attrs


