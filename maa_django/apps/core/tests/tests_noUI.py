import datetime, time
from unittest.mock import patch
from selenium import webdriver # Pour utiliser Selenium
import urllib3

from django.test import TestCase
from django.test import LiveServerTestCase, RequestFactory
from django.urls import resolve
from django.contrib.auth.models import AnonymousUser, User

from maa_django.apps.core.cdp_tools import CDPAero
from maa_django.apps.site.views import WebVFRView

# Create your tests here.        
class ConnexionTestCase(LiveServerTestCase):
    def setUp(self):
        """ executé avant toute fonction test_"""
        self.factory = RequestFactory() 
        """ un RequestFactory ne passe pas par toute la chaîne Django (dont les urls parse), il génère un objet request
        bon à fournir aux views. A contrarion, TestClient (cf self.client) permet de tester la chaîne comme si la requête venait de 
        l'extérieur"""

        self.user = User.objects.create_user(username='jacob', email='jacob@free.fr', password='top_secret')

    def tearDown(self):
        """ Executé après chaque fonction test_"""
        #self.browser.quit()

    def test_connect_to_admin(self):
        print ("No UI")
        root = resolve('/')
        self.assertEqual(root.func, WebVFRView, "L'url racine arrive n'aboutit pas sur la bonne vue")
        
        request = self.factory.get('/')
        request.user = AnonymousUser() # Simule un anonymous
        response = WebVFRView(request)
        self.assertEqual(response.status_code, 302, "L'url racine / devrait rediriger les non identifiés donc status 302")

        request.user = self.user
        #with self.assertTemplateUsed('site/inde.html', "Le template utilisé n'est pas le bon"):
        response = WebVFRView(request)
        self.assertEqual(response.status_code, 200, "L'url racine / devrait accepter les requêtes de personnes identifiées.")

    @patch("urllib3.ProxyManager.request")
    def test_recuperation_cdpaero(self, mock_request):
        mock_request.return_value.status = 200
        mock_request.return_value.data = b"""5
9552761;1;2021-09-22 12:00:00;LFPG;2021-09-22 10:00:00;9999;;;;;;;;;;;;;;;;;;;;
9552761;1;2021-09-23 12:00:00;LFPG;2021-09-22 10:00:00;9999;;;;;;;;;;;;;;;;;;;;
9552761;0;2021-09-24 06:00:00;LFPG;;;;;;;;;;;;;;;;;;;;;;
9552761;0;2021-09-22 09:00:00;LFPG;2021-09-22 05:00:00;9999;;;;40;;;;6;;;;;;;;;;;;
9552761;0;2021-09-22 15:00:00;LFPG;2021-09-22 05:00:00;9999;;;;40;;;;6;;;;;;;;;;;;
"""
        cdp = CDPAero()
        data_aero = cdp.get_remote_data_cdpaero()



    """urllib3.ProxyManager("http://proxy.meteo.fr:11011")
        try: 
            r = http.request('GET', url, timeout=10.0)
            if r.status != 200:
                print ("Erreur")
            else:
                lignes = r.data"""



    """ Test sur une urll :
        solo_detail = resolve('/solos/1/')
        self.assertEqual(
            solo_detail.func.__name__,
            'SoloDetailView'
        )
        self.assertEqual(solo_detail.kwargs['pk'], '1')
    """

    """ Creuser la différence entre resolve et reverse """

    """ Exemple de user story pour les admin
        def test_staff_can_add_content(self):
        
        #Tests that a 'staff' user can access the admin and
        #add Albums, Tracks, and Solos
        
        # Bill would like to add a record and a number of
        # solos to JMAD. He visits the admin site

        # He can tell he's in the right place because of the
        # title of the page

        # He enters his username and password and submits the
        # form to log in

        # He sees links to Albums, Tracks, and Solos
        # He clicks on Albums and sees all of the Albums that
        # have been added so far

        # Going back to the home page, he clicks the Tracks
        # link and sees the Tracks that have been added.
        # They're ordered first by Album, then by track
        # number.

        # He adds a track to an album that already exists
        # He adds another track, this time on an album that
        # is not in JMAD yet

        # After adding the basic Track info, he clicks on the
        # plus sign to add a new album.
        """

        # The focus shifts to the newly opened window, where
        # he sees an Album form

        # After creating the Album, he goes back to finish
        # the Track