'''Lens Settings
仿DRF构造settings对象

Variables:
    DEFAULTS {dict} -- [默认配置参数]
    IMPORT_STRINGS {tuple} -- [需要以模块方式导入的配置参数名]
    lens_settings {[Object]} -- [构造的settings对象]
    setting_changed.connect(reload_lens_settings) {[type]} -- [description]
'''
from __future__ import unicode_literals

from importlib import import_module

from django.conf import settings
from django.test.signals import setting_changed
# from django.utils import six

DEFAULTS = {
    # Base API policies
    'DEFAULT_VERSIONING_CLASS': 'lens.version.URLPathVersioning',

    # Versioning
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1', ],
    'VERSION_PARAM': 'version',

    # Schema
    'DEFAULT_SCHEMA_CLASS': 'lens.schema.Model',
}


# List of settings that may be in string import notation.
IMPORT_STRINGS = (
    'DEFAULT_VERSIONING_CLASS',
    'DEFAULT_SCHEMA_CLASS',
)


def perform_import(val, setting_name):
    """
    If the given setting is a string import notation,
    then perform the necessary import or imports.
    """
    if val is None:
        return None
    # elif isinstance(val, six.string_types):
    elif isinstance(val, str):
        return import_from_string(val, setting_name)
    elif isinstance(val, (list, tuple)):
        return [import_from_string(item, setting_name) for item in val]
    return val


def import_from_string(val, setting_name):
    """
    Attempt to import a class from a string representation.
    """
    try:
        # Nod to tastypie's use of importlib.
        parts = val.split('.')
        module_path, class_name = '.'.join(parts[:-1]), parts[-1]
        module = import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        msg = "Could not import '%s' for LENS setting '%s'. %s: %s." % (
            val, setting_name, e.__class__.__name__, e)
        raise ImportError(msg)


class LensSettings(object):
    """
    A settings object, that allows LENS settings to be accessed as properties.
    For example:

        from lens.settings import lens_settings
        print(lens_settings.DEFAULT_VERSIONING_CLASS)

    Any setting with string import paths will be automatically resolved
    and return the class, rather than the string literal.
    """

    def __init__(self, user_settings=None, defaults=None, import_strings=None):
        if user_settings:
            self._user_settings = user_settings
        self.defaults = defaults or DEFAULTS
        self.import_strings = import_strings or IMPORT_STRINGS
        self._cached_attrs = set()

    @property
    def user_settings(self):
        if not hasattr(self, '_user_settings'):
            self._user_settings = getattr(settings, 'LENS', {})
        return self._user_settings

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError("Invalid LENS setting: '%s'" % attr)

        try:
            # Check if present in user settings
            val = self.user_settings[attr]
        except KeyError:
            # Fall back to defaults
            val = self.defaults[attr]

        # Coerce import strings into classes
        if attr in self.import_strings:
            val = perform_import(val, attr)

        # Cache the result
        self._cached_attrs.add(attr)
        setattr(self, attr, val)
        return val

    def reload(self):
        for attr in self._cached_attrs:
            delattr(self, attr)
        self._cached_attrs.clear()
        if hasattr(self, '_user_settings'):
            delattr(self, '_user_settings')


lens_settings = LensSettings(None, DEFAULTS, IMPORT_STRINGS)


def reload_lens_settings(*args, **kwargs):
    setting = kwargs['setting']
    if setting == 'LENS':
        lens_settings.reload()


setting_changed.connect(reload_lens_settings)
