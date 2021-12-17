import base64

from django.http import HttpResponse
from django.contrib.auth import authenticate
from django.conf import settings
from django.http.response import HttpResponseForbidden


def basicauth(view):
    def wrap(self, request, *args, **kwargs):
        if 'HTTP_AUTHORIZATION' in request.META:
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2:
                if auth[0].lower() == "basic":
                    uname, passwd = base64.b64decode(auth[1]).decode(
                        "utf8"
                    ).split(':', 1)
                    user = authenticate(username=uname, password=passwd)
                    if user is not None and user.is_active:
                        request.user = user
                        return view(self, request, *args, **kwargs)
        
        response = HttpResponse()
        response.status_code = 401
        response['WWW-Authenticate'] = 'Basic realm="{}"'.format(
            settings.BASIC_AUTH_REALM
        )
        return response
    return wrap


def has_perm_expair(view):
    @basicauth
    def wrap(self, request, *args, **kwargs):
        if not request.user.has_perm('analyseur.envoimaa_manuel'):
            return HttpResponseForbidden("Vous n'avez pas les droits suffisants pour exécuter cette action.")

        return view(self, request, *args, **kwargs)
    return wrap