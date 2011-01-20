from mongoadmin.views import MongoAdmin, site
from mongoadmin.forms import MongoAdminForm

def autodiscover(*args):
    ''' Discover submodules in Django apps that would otherwise be
        ignored (listeners, configforms, etc)

        Usage: autodiscover('configforms'[, 'listeners'[, ...]])
    '''
    from django.conf import settings
    from django.utils.importlib import import_module
    from django.utils.module_loading import module_has_submodule

    for submod in args:
        for app in settings.INSTALLED_APPS:
            mod = import_module(app)
            if module_has_submodule(mod, submod):
                import_module('%s.%s' % (app, submod))
