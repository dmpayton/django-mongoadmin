from django.conf import settings
from django.conf.urls.defaults import patterns, url
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import logout
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db.models.options import get_verbose_name
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.decorators import method_decorator
from django.utils.encoding import force_unicode
from django.utils.functional import update_wrapper
from django.utils.translation import ugettext_lazy, ugettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from mongoadmin.forms import MongoAdminForm
from mongoengine import Document
from mongoengine.django.shortcuts import get_document_or_404, get_list_or_404

LOGIN_FORM_KEY = 'this_is_the_login_form'

class MongoAdmin(object):
    group = 'Documents'
    list_items = []
    verbose_name = None
    verbose_name_plural = None
    form = MongoAdminForm

    def __init__(self, model):
        self.model = model

        self.model_name = self.model._class_name

        ## Set defaults
        if not self.list_items:
            self.list_items.append('__unicode__')
        if not self.verbose_name:
            self.verbose_name = get_verbose_name(self.model_name)
        if not self.verbose_name_plural:
            self.verbose_name_plural = '%ss' % self.verbose_name

        ## Validations
        for attr in self.list_items:
            if not hasattr(self.model, attr):
                raise ValueError('%s is not an attribute of %s' % (attr, self.model._class_name))

        if not issubclass(MongoAdminForm, self.form):
            raise TypeError('Form must be subclass of MongoAdminForm')

    def _get_items(self, document):
        item = []
        for attr in self.list_items:
            if hasattr(self, attr):
                value = getattr(self, attr)
                if callable(value):
                    value = value(document=document)
            elif hasattr(document, attr):
                value = getattr(document, attr)
                if callable(value):
                    value = value()
            else:
                raise Exception(_('No attribute %(attr)s found for %(name)s') % {'attr': field, 'name': self.verbose_name})
            item.append(value)
        return item

    def get_form(self, *args, **kwargs):
        class ThisMongoAdminForm(self.form):
            class Meta:
                document = self.model
        return ThisMongoAdminForm(self, *args, **kwargs)

class MongoAdminSite(object):
    def __init__(self):
        self._registry = {}

    def register(self, cls, admin=None):
        admin = admin or MongoAdmin
        if not issubclass(cls, Document):
            raise TypeError('Registered documents must be a subclass of mongoengine.Document')
        if not issubclass(admin, MongoAdmin):
            raise TypeError('Document admins must be a subclass of mongoadmin.MongoAdmin')
        if cls in self._registry:
            raise ValueError('%s is already registered')
        self._registry[cls._meta['collection']] = (cls, admin(cls))

    def unregister(self, cls):
        if cls in self._registry:
            del self._registry[cls]

    def verify_collection(self, collection):
        if collection not in self._registry:
            raise Http404('%s collection not found.' % collection)
        return self._registry[collection]

    def display_login_form(self, request, error_message='', extra_context=None):
        request.session.set_test_cookie()
        context = {
            'title': _('Log in'),
            'app_path': request.get_full_path(),
            'error_message': error_message,
            'root_path': 'WUT',
        }
        context.update(extra_context or {})
        return render_to_response('admin/login.html', context,
            context_instance=RequestContext(request))

    def has_permission(self, user):
        return user.is_active and (user.is_staff or user.is_superuser)

    def admin_view(self, view):
        @csrf_protect
        def inner(request, *args, **kwargs):
            if not self.has_permission(request.user):
                return self.login(request)
            return view(request, *args, **kwargs)
        return update_wrapper(inner, view)

    @property
    def urls(self):
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        urlpatterns = patterns('',
            url(r'^$', wrap(self.index_view), name='index'),
            url(r'^jsi18n/$', wrap(self.i18n_javascript), name='jsi18n'),
            url(r'^login/$', wrap(self.login), name='login'),
            url(r'^logout/$', wrap(self.logout), name='logout'),
            url(r'^(?P<collection>\w+)/$', wrap(self.changelist_view), name='changelist'),
            url(r'^(?P<collection>\w+)/add/$', wrap(self.change_view), name='add'),
            url(r'^(?P<collection>\w+)/(?P<object_id>[0-9a-fA-F]+)/$', wrap(self.change_view), name='change'),
            url(r'^(?P<collection>\w+)/(?P<object_id>[0-9a-fA-F]+)/delete/$', wrap(self.delete_view), name='delete'),
        )

        return urlpatterns

    @method_decorator(never_cache)
    def login(self, request):
        # If this isn't already the login page, display it.
        if not request.POST.has_key(LOGIN_FORM_KEY):
            if request.POST:
                message = _('Please log in again, because your session has expired.')
            else:
                message = ''
            return self.display_login_form(request, message)

        # Check that the user accepts cookies.
        if not request.session.test_cookie_worked():
            message = _("Looks like your browser isn't configured to accept cookies. Please enable cookies, reload this page, and try again.")
            return self.display_login_form(request, message)
        else:
            request.session.delete_test_cookie()

        # Check the password.
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if not user:
            message = _('Sorry, the username or password you entered is invalid.')
            return self.display_login_form(request, message)

        ## Admins only
        if not self.has_permission(user):
            message = _('Only staff members and site administrators are allowed to access this page.')
            return self.display_login_form(request, message)

        ## Made it this far, we're good to go
        login(request, user)
        return HttpResponseRedirect(request.path)

    @method_decorator(never_cache)
    def logout(self, request):
        return logout(request)

    def i18n_javascript(self, request):
        """
        Displays the i18n JavaScript that the Django admin requires.

        This takes into account the USE_I18N setting. If it's set to False, the
        generated JavaScript will be leaner and faster.
        """
        if settings.USE_I18N:
            from django.views.i18n import javascript_catalog
        else:
            from django.views.i18n import null_javascript_catalog as javascript_catalog
        return javascript_catalog(request, packages='django.conf')

    @method_decorator(never_cache)
    def index_view(self, request):
        doc_list = []
        for collection, (cls, admin) in self._registry.iteritems():
            doc_list.append({
                'group': admin.group,
                'name': admin.verbose_name,
                'collection': cls._meta['collection']
                })
        return render_to_response('mongoadmin/index.html', {
            'title': _('MongoDB Administration'),
            'doc_list': doc_list
            }, context_instance=RequestContext(request))

    @method_decorator(never_cache)
    def changelist_view(self, request, collection):
        cls, admin = self.verify_collection(collection)
        queryset = cls.objects.all()
        document_list = [(document, admin._get_items(document)) for document in queryset]
        return render_to_response('mongoadmin/change_list.html', {
            'document_list': document_list,
            'collection': collection,
            'admin': admin,
            'title': _('Select %s to change') % admin.verbose_name
            }, context_instance=RequestContext(request))

    @method_decorator(never_cache)
    def change_view(self, request, collection, object_id=None):
        cls, admin = self.verify_collection(collection)
        if object_id:
            document = get_document_or_404(cls, id=object_id)
            form = admin.get_form(request.POST or None, instance=document)
            add, change = False, True
        else:
            document = None
            form = admin.get_form(request.POST or None)
            add, change = True, False

        if form.is_valid():
            document = form.save()
            msg = _('The %(name)s "%(obj)s" was saved successfully.') % {'name': force_unicode(admin.verbose_name), 'obj': force_unicode(document)}
            if '_continue' in request.POST:
                redirect_url = reverse('mongoadmin:change', args=(collection, str(document.pk)))
                msg += ' ' + _('You may edit it again below.')
            elif '_addanother' in request.POST:
                redirect_url = reverse('mongoadmin:add', args=(collection,))
                msg += ' ' + (_('You may add another %s below.') % force_unicode(admin.verbose_name))
            else:
                redirect_url = reverse('mongoadmin:changelist', args=(collection,))

            messages.info(request, msg)
            return HttpResponseRedirect(redirect_url)

        return render_to_response('mongoadmin/change_form.html', {
            'document': document,
            'form': form,
            'collection': collection,
            'admin': admin,
            'add': add,
            'change': change,
            'title': _('Change %s') % admin.verbose_name
            }, context_instance=RequestContext(request))

    @method_decorator(never_cache)
    def delete_view(self, request, collection, object_id):
        cls, admin = self.verify_collection(collection)
        document = get_document_or_404(cls, id=object_id)
        if request.method == 'POST':
            document.delete()
            msg = _('The %(name)s "%(obj)s" has been deleted.') % {'name': force_unicode(admin.verbose_name), 'obj': force_unicode(document)}
            messages.info(request, msg)
            return HttpResponseRedirect(reverse('mongoadmin:changelist', args=(collection,)))
        return render_to_response('mongoadmin/delete_confirmation.html', {
            'document': document,
            'collection': collection,
            'admin': admin,
            'title': _('Delete %s') % admin.verbose_name
            }, context_instance=RequestContext(request))



site = MongoAdminSite()
