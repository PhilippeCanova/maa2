from django.contrib import admin


from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Profile
from django.contrib.auth.models import User

from profiles.models import Profile


class UserProfileInline(admin.StackedInline):
    model = Profile

class NewUserAdmin(UserAdmin):
    inlines = [UserProfileInline]

admin.site.unregister(User)
admin.site.register(User, NewUserAdmin)


# Register your models here.
#admin.site.register(Profile)