from everest.resources.base import Collection
from everest.resources.base import Member


class FooMember(Member):
    relation = 'http://everest.org/relations/foomember'


class BarMember(Member):
    relation = 'http://everest.org/relations/barmember'


class FooCollection(Collection):
    title = 'My Foo Collection'
    root_name = 'foos'
    description = 'My fancy Foo collection.'
    max_limit = 1000


class BarCollection(Collection):
    title = 'My Bar Collection'
    root_name = 'bars'
    description = 'My fancy Bar collection.'
