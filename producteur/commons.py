import os
from datetime import datetime

from mflog import get_logger

from analyseur.models import EnvoiMAA 
from producteur.pdf_tools import create_MAA_pdf_from_envoimaa

def check_production():
    """ Regarde s'il y a des envoi maa à convertir en PDF """
    logger = get_logger("check production")
    envois = EnvoiMAA.objects.filter(status = 'to_create')
    for envoi in envois:
        pdf_temp = None
        log = envoi.log
        try:
            envoi, pdf_temp = create_MAA_pdf_from_envoimaa(envoi)
            envoi.status = 'to_send'
        except Exception as e:
                log = log + "\n" + "{}:\n Impossible de créer le PDF pour le MAA.".format(datetime.utcnow())
                log = log + "\n" + "{} - {} - {} - {}".format(  envoi.configmaa, 
                                                                envoi.date_debut, 
                                                                envoi.date_fin, 
                                                                envoi.numero)
                log = log + "\n" + str(e)            
                pdf_temp = None
                print(log)

        envoi.log = log
        envoi.save()
        
        if pdf_temp is not None: 
            os.remove(pdf_temp)

def check_to_send():
    """ Vérifie s'il y a quelque chose à envoyer """
    logger = get_logger("check production")
    envois = EnvoiMAA.objects.filter(status = 'to_send')
    for envoi in envois:
        #TODO: gérer la production pour de vrai. 
        logger.info("Simule l'envoi du MAA {}".format(str(envoi)))
        envoi.status = 'ok'
        envoi.save()

def analyse_1mn():
    """ Vérifie régulièrement si des maa ont été initiés mais pas encore produits (pdf) et diffusés.
    Se charge alors de ces deux actions """
    logger = get_logger("check production")

    logger.info(f"Vérification des besoins de production...")
    check_production()
    
    logger.info(f"Vérification des besoins de diffusion...")
    check_to_send()
