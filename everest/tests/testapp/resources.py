from everest.resources.base import Collection
from everest.resources.base import Member


class FooMember(Member):
    relation = 'http://everest.org/relations/foomember'


class BarMember(Member):
    relation = 'http://everest.org/relations/barmember'


class FooCollection(Collection):
    title = 'My Foo Collection'
    root_name = 'my-foo-collection'
    description = 'My fancy Foo collection.'


class BarCollection(Collection):
    title = 'My Bar Collection'
    root_name = 'my-bar-collection'
    description = 'My fancy Bar collection.'
