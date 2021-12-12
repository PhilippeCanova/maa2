from pathlib import Path
import io
from datetime import datetime 
import asyncio, urllib3
from urllib3 import ProxyManager

from django.conf import settings
from django.core.files import File
from django.urls import reverse

from configurateur.models import Region, Station, ConfigMAA
from analyseur.models import EnvoiMAA
from profiles.models import Profile

def create_MAA_pdf_from_envoimaa(envoi):
    """ Lance la création d'un PDF à partir d'un objet EnvoiMAA """
    try:
        base_dir = Path(__file__).parent
        name = "MAA_{}_{}_{}_{}.pdf".format(
                    envoi.configmaa.station.oaci, 
                    envoi.configmaa.type_maa, 
                    envoi.configmaa.seuil,
                    envoi.date_envoi,
                    )
        chemin = base_dir.joinpath('tmp').joinpath(name) #TODO: dans les tests, vérifier la présence du répertoire tmp dans cette app.
        #TODO: il y a sans doute moyen de passer par un fichier temporaire en mémoire
        url = reverse('view_product_maa', args=[envoi.pk])
        asyncio.run(html_to_pdf(url, chemin))
        with open(chemin, 'rb') as f:
            envoi.message_pdf.save(name, File(f))
        envoi.save()
    except Exception as e:
        message = "\n{}".format(datetime.utcnow()) + str(e)
        envoi.log = envoi.log + "\n{}".format(datetime.utcnow()) + str(e)
        raise SystemError(message)
    return envoi, chemin

async def html_to_pdf(url, pdf_file):
    try:
        from pyppeteer import launch
    except ImportError:
        print(
            "Generating PDF from book HTML requires the pyppeteer package. "
            "Install it first.",
            ImportError,
        )
    browser = await launch( executablePath= '/usr/lib64/chromium-browser/headless_shell',
                            #args=["--no-sandbox"], 
                            handleSIGINT=False,
                            handleSIGTERM=False,
                            handleSIGHUP=False)
    page = await browser.newPage()

    # Waiting for networkidle0 seems to let mathjax render
    print("html_to_pdf", settings.RUNNING_SERVER)
    url = "http://localhost:18868" + url #TODO: adresse en dur à virer
    print ("html_to_pdf", url)

    await page.goto( url , {"waitUntil": ["networkidle0"]})
    # Give it *some* margins to make it look a little prettier
    # I just made these up
    page_margins = {"left": "0in", "right": "0in", "top": "0mm", "bottom": "0in"}
    await page.pdf({"path": pdf_file, "margin": page_margins})
    await browser.close() 

    
    