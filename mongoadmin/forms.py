from django import forms
from django.conf import settings
from django.contrib.admin import widgets
from mongoforms import MongoForm

FORM_WIDGETS = {
    'fields': {
        forms.DateTimeField: widgets.AdminSplitDateTime,
        forms.DateField: widgets.AdminDateWidget,
        forms.TimeField: widgets.AdminTimeWidget,
        forms.URLField: widgets.AdminURLFieldWidget,
        forms.IntegerField: widgets.AdminIntegerFieldWidget,
        #forms.ImageField: widgets.AdminFileWidget, ## TODO: How to handle these?
        #forms.FileField: widgets.AdminFileWidget,
        },
    'widgets': {
        forms.Textarea: widgets.AdminTextareaWidget,
        forms.TextInput: widgets.AdminTextInputWidget,
        }
}

class MongoAdminForm(MongoForm):
    def __init__(self, admin, *args, **kwargs):
        self._admin = admin
        super(MongoAdminForm, self).__init__(*args, **kwargs)
        for key, field in self.fields.items():
            if field.__class__ in FORM_WIDGETS['fields']:
                self.fields[key].widget = FORM_WIDGETS['fields'][field.__class__]()
            elif field.widget.__class__ in FORM_WIDGETS['widgets']:
                self.fields[key].widget = FORM_WIDGETS['widgets'][field.widget.__class__]()

    def _media(self):
        form_media = forms.Media(js=(settings.ADMIN_MEDIA_PREFIX + 'js/core.js',))
        form_media += super(MongoAdminForm, self).media
        return form_media
    media = property(_media)
