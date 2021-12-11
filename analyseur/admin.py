from django.contrib import admin

from .models import EnvoiMAA
# Register your models here.
class EnvoiMAAAdmin(admin.ModelAdmin):

    list_display = ('numero', 'date_envoi', 'status', 'configmaa')
    #search_fields = ['numero']
    date_hierarchy = 'date_envoi'

admin.site.register(EnvoiMAA, EnvoiMAAAdmin)