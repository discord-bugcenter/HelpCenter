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

cached_users_locals = {}


def get_translation(message: str, target: Optional[discord.User | discord.Member | discord.Interaction] = None):
    if not target:
        locale = LOCALE_DEFAULT
    elif isinstance(target, discord.User) or isinstance(target, discord.Member):
        if cached_users_locals.get(target.id):
            locale = cached_users_locals[target.id]
        else:
            locale = LOCALE_DEFAULT
    else:
        locale = target.locale.value
        cached_users_locals[target.user.id] = locale

    if not gettext_translations:
        return gettext.gettext(message)

    return (
        gettext_translations.get(
            locale,
            gettext_translations[LOCALE_DEFAULT]
        ).gettext(message)
    )


_ = get_translation
