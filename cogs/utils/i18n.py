#  i18n for discord bot, source here :
#  https://github.com/XuaTheGrate/i18n/blob/master/i18n.py

import gettext
import os.path
from glob import glob
from typing import Optional

import discord

BASE_DIR = "ressources/"  # change this if you store your files under `src/` or similar
LOCALE_DEFAULT = 'en-US'
LOCALE_DIR = "locale"
locales = frozenset(map(os.path.basename, filter(os.path.isdir, glob(os.path.join(BASE_DIR, LOCALE_DIR, '*')))))


gettext_translations = {
    locale: gettext.translation(
        'help_center',
        languages=(locale,),
        localedir=os.path.join(BASE_DIR, LOCALE_DIR))
    for locale in locales}

gettext_translations['en-US'] = gettext.NullTranslations()
locales |= {'en-US'}


def get_translation(message, inter: Optional[discord.Interaction] = None):
    if not inter:
        locale = LOCALE_DEFAULT
    else:
        locale = inter.locale.value

    if not gettext_translations:
        return gettext.gettext(message)

    return (
        gettext_translations.get(
            locale,
            gettext_translations[LOCALE_DEFAULT]
        ).gettext(message)
    )


_ = get_translation
