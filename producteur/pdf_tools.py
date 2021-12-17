from pathlib import Path
import io
from datetime import datetime 
import asyncio, urllib3
from urllib3 import ProxyManager

from mflog import get_logger

from django.conf import settings
from django.core.files import File
from django.urls import reverse

from configurateur.models import Region, Station, ConfigMAA
from analyseur.models import EnvoiMAA
from profiles.models import Profile

def create_MAA_pdf_from_envoimaa(envoi):
    """ Lance la création d'un PDF à partir d'un objet EnvoiMAA """
    logger = get_logger("creation_pdf")
    try:

        base_dir = Path(__file__).parent
        name = "MAA_{}_{}_{}_{}.pdf".format(
                    envoi.configmaa.station.oaci, 
                    envoi.configmaa.type_maa, 
                    envoi.configmaa.seuil,
                    envoi.date_envoi,
                    )
        logger.info("Lancement de la création du fichier {}...".format(name))
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
        logger.critical("La création du PDF {} a échoué pour la raison suivante : \n".format(name) + str(e))
        raise SystemError(message)
    return envoi, chemin

async def html_to_pdf(url, pdf_file):
    logger = get_logger("creation_pdf")
    try:
        from pyppeteer import launch
    except ImportError:
        print(
            "Generating PDF from book HTML requires the pyppeteer package. "
            "Install it first.",
            ImportError,
        )
        logger.critical("Installation du pyppeteer nécessaire")

    browser = await launch( executablePath= '/usr/lib64/chromium-browser/headless_shell',
                            #args=["--no-sandbox"], 
                            handleSIGINT=False,
                            handleSIGTERM=False,
                            handleSIGHUP=False)
    page = await browser.newPage()

    url = settings.RUNNING_SERVER + url 

    logger.info("Url de récupération du MAA : {}".format(url))

    http = urllib3.PoolManager()
    resp = http.request('GET', url)
    print(resp.status, url)

    await page.goto( url , {"waitUntil": ["networkidle0"]})
    # Give it *some* margins to make it look a little prettier
    # I just made these up
    page_margins = {"left": "0in", "right": "0in", "top": "0mm", "bottom": "0in"}
    await page.pdf({"path": pdf_file, "margin": page_margins})
    await browser.close()
    logger.info("Fin de la création du fichier")

    
    