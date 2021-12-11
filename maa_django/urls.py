"""maa_django URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from maa_django.apps.site.views import update_profile, create_profile
from maa_django.apps.core.views import ListRegions, ListStations, DetailStation, DetailStationOACI, ConfigMAAStation
from maa_django.apps.core.views import ListConfigMAA

from analyseur.views import SetManuelMAA
from producteur.views import ProductMAA
from donneur.views import RetrievePastDatasView

#from rest_framework.documentation import include_docs_urls

urlpatterns = [
    path('accounts/login/', auth_views.LoginView.as_view(template_name='core/registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(template_name='core/registration/logged_out.html'), name='logout'),
    path('accounts/update/', update_profile, name='accountsupdate'),
    path('accounts/create/', create_profile, name='accountscreate'),

    path('adminMAA/', admin.site.urls),
    path('', include('maa_django.apps.site.urls'), name='accueil'),

    path('api/regions/', ListRegions.as_view(), name='liste_regions'),
    path('api/stations/', ListStations.as_view(), name='liste_stations'),
    path('api/station/<str:oaci>/config_maa/', ConfigMAAStation.as_view(), name='config_maastation'),
    path('api/station/<int:pk>/', DetailStation.as_view(), name='detail_station_id'),
    path('api/station/<str:oaci>/', DetailStationOACI.as_view(), name='detail_station_oaci'),
    path('api/configs_maa/', ListConfigMAA.as_view(), name='liste_config_maa'),
    #path('api/docs/', include_docs_urls(title='Mes API DRF')),
    
    #    url(r'^about/$', TemplateView.as_view(template_name="python/about.html"), name='about'),
    # Permet de lancer une vue avec peu de valeur ajoutée
    path('api/configs_maa/maa_config.php', SetManuelMAA.as_view(), name='set_manuel_maa'), #Soumettre des MAA mauellement
    path('maa/product/<int:pk>/', ProductMAA.as_view(), name='view_product_maa'), # Visualiser un produit MAA pour en faire un export PDF
    path('datas/past/', RetrievePastDatasView.as_view(), name='past_data'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# ADDED BY METWORK/MFSERV/DJANGO PLUGIN TEMPLATE
# TO PROVIDE PREFIX BASED ROUTING
from django.conf.urls import include, url
PREFIXES = [r"^maa_django/"]
urlpatterns = [url(x, include(urlpatterns)) for x in PREFIXES]
