"""
Resource reference expression parser.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 31, 2014.
"""
from pyparsing import CaselessKeyword
from pyparsing import Combine
from pyparsing import Group
from pyparsing import Literal
from pyparsing import Word
from pyparsing import ZeroOrMore
from pyparsing import alphanums
from pyparsing import alphas
from pyparsing import delimitedList
from pyparsing import replaceWith

from everest.constants import ResourceReferenceRepresentationKinds
from everest.entities.utils import identifier_from_slug
from everest.representers.config import IGNORE_OPTION
from everest.representers.config import WRITE_AS_LINK_OPTION


__docformat__ = 'reStructuredText en'
__all__ = ['parse_refs',
           ]

TILDE_PAT = '~'
URL_PAT = ResourceReferenceRepresentationKinds.URL
INLINE_PAT = ResourceReferenceRepresentationKinds.INLINE
OFF_PAT = ResourceReferenceRepresentationKinds.OFF

URL = CaselessKeyword("url").setParseAction(replaceWith(URL_PAT))
INLINE = CaselessKeyword("inline").setParseAction(replaceWith(INLINE_PAT))
OFF = CaselessKeyword("off").setParseAction(replaceWith(OFF_PAT))


class RefsConverter(object):
    """
    Converter for a sequence of resource references.
    """
    @classmethod
    def convert(cls, toks):
        config = {}
        for rf in toks:
            config.update(cls.__convert_ref(rf))
        return config

    @classmethod
    def __convert_ref(cls, rf):
        names = [identifier_from_slug(token)
                 for token in rf.attribute.split('.')]
        config = {}
        # First, make sure that all parent attributes are configured INLINE.
        for idx in range(len(names[:-1])):
            key = tuple(names[:idx + 1])
            config[key] = {IGNORE_OPTION:False,
                           WRITE_AS_LINK_OPTION:False}
        is_off = rf.option == OFF_PAT
        opts = {IGNORE_OPTION:is_off}
        if not is_off:
            opts[WRITE_AS_LINK_OPTION] = rf.option == URL_PAT
        config[tuple(names)] = opts
        return config


colon = Literal(':')
attribute = Word(alphas, alphanums + '-')
identifier = \
    Combine(attribute + ZeroOrMore('.' + attribute)).setName('identifier')
option = (URL | INLINE | OFF)
ref = Group(identifier('attribute')
                  + colon.suppress()
                  + option('option'))
refs = delimitedList(ref, delim=TILDE_PAT)
refs.setParseAction(RefsConverter.convert)


def parse_refs(refs_string):
    return refs.parseString(refs_string)[0]
