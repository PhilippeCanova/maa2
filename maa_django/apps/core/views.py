from django.db.models.query import QuerySet
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
from django.views import generic

from rest_framework import generics
import json , datetime, random
from configurateur.models import ConfigMAA, Region, Station
from .serializers import RegionsSerializer, StationsSerializer, StationConfigMAASerializer, ConfigsMAASerializer
from rest_framework.response import Response

class ListRegions(generics.ListAPIView):
    queryset = Region.objects.all()
    serializer_class = RegionsSerializer

class ListStations(generics.ListAPIView):
    queryset = Station.objects.all()
    serializer_class = StationsSerializer

class DetailStation(generics.RetrieveAPIView):
    queryset = Station.objects.filter(active = True)
    serializer_class = StationsSerializer
class DetailStationOACI(generics.RetrieveAPIView):
    queryset = Station.objects.filter(active = True)
    serializer_class = StationsSerializer
    lookup_field='oaci'
class ListConfigMAA(generics.ListAPIView):
    queryset = ConfigMAA.objects.all()
    serializer_class = ConfigsMAASerializer
class ConfigMAAStation(generics.ListAPIView):
    serializer_class = ConfigsMAASerializer
    queryset = ConfigMAA.objects.all()

    def filter_queryset(self, queryset):
        station = self.kwargs.get('oaci')
        return queryset.filter(station__oaci=station)