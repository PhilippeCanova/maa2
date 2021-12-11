from django.urls import path

from . import views


urlpatterns = [
    path('', views.WebVFRView, name='accueil'),
]