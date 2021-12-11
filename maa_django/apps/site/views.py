from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils.translation import gettext as _
from django.shortcuts import redirect

from django.utils.translation import activate, get_language_info

from django.contrib.auth import login, authenticate

from .forms import ProfileForm, UserForm, UserFormChange

@login_required
@transaction.atomic
def update_profile(request):
    if request.method == 'POST':
        user_form = UserFormChange(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            
            messages.success(request, _('Your profile was successfully updated!'))
            return redirect('accueil')
        else:
            messages.error(request, _('Please correct the error below.'))
    else:
        user_form = UserFormChange(instance=request.user)
        profile_form = ProfileForm(instance=request.user.profile)
    return render(request, 'site/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

@transaction.atomic
def create_profile(response):
    if response.method == 'POST':
        user_form = UserForm(response.POST)
        
        if user_form.is_valid():
            user = user_form.save()
            user.refresh_from_db() 
            #user.profile.airport = profile_form.cleaned_data.get('airport')
            profile_form = ProfileForm(response.POST, instance=user.profile)
            if profile_form.is_valid():
                profile_form.save()

            username = user_form.cleaned_data.get('username')
            raw_password = user_form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(response, user)

            messages.success(response, _('Your profile was successfully updated!'))
            login(response, user)
            return redirect('accueil')
    else:
        user_form = UserForm()
        profile_form = ProfileForm()
    return render(response, 'site/profile.html', {
            'user_form': user_form,
            'profile_form': profile_form
        })
    

@login_required
def WebVFRView(request):
    print(get_language_info('fr'))
    context = request.user.groups
    print(request.user.id)
    print(request.user.username)
    #print(request.user.get_group_permissions())
    print(request.user.groups.all())
    print(request.user.profile.region)
    return render(request, 'site/index.html', {})

