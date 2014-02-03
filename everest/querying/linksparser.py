"""
Link configuration expression parser.

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

from everest.entities.utils import identifier_from_slug
from everest.representers.config import IGNORE_OPTION
from everest.representers.config import WRITE_AS_LINK_OPTION


__docformat__ = 'reStructuredText en'
__all__ = ['parse_links',
           ]

TILDE_PAT = '~'
URL_PAT = 'URL'
INLINE_PAT = 'INLINE'
OFF_PAT = 'OFF'

URL = CaselessKeyword("url").setParseAction(replaceWith(URL_PAT))
INLINE = CaselessKeyword("inline").setParseAction(replaceWith(INLINE_PAT))
OFF = CaselessKeyword("off").setParseAction(replaceWith(OFF_PAT))


class LinksConverter(object):
    @classmethod
    def convert(cls, toks):
        config = {}
        for lnk in toks:
            config.update(cls.__convert_link(lnk))
        return config

    @classmethod
    def __convert_link(cls, lnk):
        names = [identifier_from_slug(token)
                 for token in lnk.attribute.split('.')]
        config = {}
        # First, make sure that all parent attributes are configured INLINE.
        for idx in range(len(names[:-1])):
            key = tuple(names[:idx + 1])
            config[key] = {IGNORE_OPTION:False,
                           WRITE_AS_LINK_OPTION:False}
        is_off = lnk.option == OFF_PAT
        opts = {IGNORE_OPTION:is_off}
        if not is_off:
            opts[WRITE_AS_LINK_OPTION] = lnk.option == URL_PAT
        config[tuple(names)] = opts
        return config



colon = Literal(':')
attribute = Word(alphas, alphanums + '-')
identifier = \
    Combine(attribute + ZeroOrMore('.' + attribute)).setName('identifier')
option = (URL | INLINE | OFF)
link = Group(identifier('attribute')
                  + colon.suppress()
                  + option('option'))
links = delimitedList(link, delim=TILDE_PAT)
links.setParseAction(LinksConverter.convert)


def parse_links(links_string):
    return links.parseString(links_string)[0]
