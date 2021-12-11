from django.contrib import admin
from django.conf.urls import url
from django import forms
from django.contrib.admin.models import LogEntry
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect


from configurateur.models import Region, Station, ConfigMAA
from profiles.models import Profile
from configurateur.models import Client, MediumFTP, MediumMail, MediumSMS, AutorisedMAAs
from maa_django.apps.core.models import Log 





class LogAdmin(admin.ModelAdmin):
    list_display = ('heure', 'machine', 'type', 'code', 'message')
    search_fields = ['heure', 'machine', 'type']



"""class ConfigMAAForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(ConfigMAAForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        print(self.user)
        if instance:        
            self.fields['pause'].widget.attrs['readonly'] = True
            self.fields['scan'].widget.attrs['readonly'] = True
            #self.fields['profondeur'].widget.attrs['readonly'] = True
    class Meta:
        model = ConfigMAA
        #exclude = ['pause', 'scan', 'profondeur']
        fields = ('station','type_maa','seuil','auto','pause','scan')"""






"""from django.views.decorators.cache import never_cache
class CustomAdminSite(admin.AdminSite):
    @never_cache
    def index(self, request, extra_context=None):
        pass 

    def get_urls(self):
        urls = super(CustomAdminSite, self).get_urls()
        custom_urls = [
            url(r'desired/path$',self.admin_view(organization_admin.preview), name="preview"), 
        ]
        return urls + custom_urls            print(request)
            print(request.get_full_path())
    
custom_admin_site = CustomAdminSite()
custom_admin_site.register(ConfigMAA, ConfigMAAAdmin)"""



# Register your models here.

admin.site.register(Region)
admin.site.register(Log, LogAdmin)


class HistoryAdmin(admin.ModelAdmin):
    list_display = ('object_repr', 'action_flag', 'action_time', 'user')
admin.site.register(LogEntry, HistoryAdmin)
