#  i18n for discord bot, source here :
#  https://github.com/XuaTheGrate/i18n/blob/master/i18n.py

import builtins
import contextvars
import gettext
import os.path
from glob import glob

BASE_DIR = "ressources/"  # change this if you store your files under `src/` or similar
LOCALE_DEFAULT = 'en_US'
LOCALE_DIR = "locale"
locales = frozenset(map(os.path.basename, filter(os.path.isdir, glob(os.path.join(BASE_DIR, LOCALE_DIR, '*')))))


gettext_translations = {
    locale: gettext.translation(
        'help_center',
        languages=(locale,),
        localedir=os.path.join(BASE_DIR, LOCALE_DIR))
    for locale in locales}

gettext_translations['en_US'] = gettext.NullTranslations()
locales |= {'en_US'}


def use_current_gettext(*args, **kwargs):
    if not gettext_translations:
        return gettext.gettext(*args, **kwargs)

    locale = current_locale.get()
    return (
        gettext_translations.get(
            locale,
            gettext_translations[LOCALE_DEFAULT]
        ).gettext(*args, **kwargs)
    )


current_locale = contextvars.ContextVar('i18n')
current_locale.set(LOCALE_DEFAULT)

