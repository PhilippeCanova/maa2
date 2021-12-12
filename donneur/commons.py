"""
    Module servant d'interface entre le système MAA et les données externalisées (données TAF, CDP H/Q...)
    
    L'objectif est de faire en sorte que le système MAA voit un seul format de données avec les données requises
    pour le reste, indépendamment du moyen de les récupérer.  
"""
import urllib3
from datetime import datetime as dt
from datetime import timedelta
from math import ceil

from django.conf import settings
from configurateur.models import Station

PROXY_METEO = "http://proxy.meteo.fr:11011"

''' Non utile car charge séparément la métropole et l'outre-mer directement dans le provide_manager
à vérifier si on peut supprimer
def retrieveDatas(stations = None):
    """ Fonction allant chercher les données aéro et cdp d'une liste de stations.
    La liste représente une liste de tuple (code oaci=>str, code insee=>str, outremer=>bool) 
    outremer vaut True si la station est en outre-mer 

    Retourne le tuple (données aero, données cdph, données 2cdpq)
    """
    stations_datas_aero = {} # Stoques les infos récupérées pour chaque station dans le cdp aero
    stations_datas_cdph = {} # Stoques les infos récupérées pour chaque station dans le cdph
    stations_datas_cdpq = {} # Stoques les infos récupérées pour chaque station dans le cdpq

    # Récupération des données cdph
    stations_datas_cdph.update(retrieveDatasCDPH_metropole(stations))

    # Récupération des données cdpq
    stations_datas_cdpq.update(retrieveDatasCDPQ_metropole(stations))

    # Récupération des données aéro
    stations_datas_aero.update(retrieveDatasAero(stations))

    return stations_datas_aero, stations_datas_cdph, stations_datas_cdpq
'''

def request_data_cdp(url):
    """ Va chercher les données sur le SA CDP Aéro"""
    data = None
    http = urllib3.ProxyManager(PROXY_METEO)
    try: 
        r = http.request('GET', url, timeout=10.0)
            
        if r.status != 200:
            print ("De requête du cdp aéro : {}\nCode retour : {}".format(url, r.status))
            #TODO: faire une remontée de log WARNING si n'arrive pas à joindre le WS
        else:
            data = r.data.decode('utf-8')
    except urllib3.exceptions.RequestError as E:
        print (E)
    #TODO: si pas de données (donc data=None) loguer un warning
    return data

def retrieveDatasAero(stations = None, remote_url = settings.REMOTE_CDPAERO):
    """ Fonction allant chercher les données aéro d'une liste de station. 
    La liste représente les tuple (oaci, insee) des stations. 
    
    Retourne un dictionnaire { oaci: [lignes récupérées] }
    """
    #http://nihoa-v27b.meteo.fr/cdp1/aerop?dpivot=-3,48&format=csv&param=idoaci,id,typeprev,dvalid,DateEmissionTAF,visi,visiprob40,VisibiliteTempo,VisibiliteProb40Tempo,ddtaf,DDTAFTempo,DDTAFProb40,DDTAFProb40Tempo,FFTAF,FFTAFTempo,FFTAFProb40,FFTAFProb40Tempo,FXTAF,FXTAFTempo,FXTAFProb40,FXTAFProb40Tempo,wwTAF,wwTAFTempo,wwTAFProb40,wwTAFProb40Tempo&id=6929961&ordre=dvalid&cond=(typeprev=0)%20and%20(DateEmissionTAF!=%27%27)
    reponse = {}
    parametres = {}
    parametres['dpivot'] = "-3,48"  # Permet de faire la demande sur -3h à 48h 
    parametres['format'] = 'csv'    # Réponse du SA CDP en csv 
    parametres['param'] = ','.join(AeroDataHoraire.PARAMETRES_CDP_AERO)
    parametres['id'] = ",".join([insee for oaci, insee, om in stations])
    parametres['ordre'] = 'dvalid'
    parametres['cond']="(typeprev=0)%20and%20(DateEmissionTAF!=%27%27)"
    
    # Définit l'url : 
    url = remote_url + "&".join([parametre + "=" + value for parametre, value in parametres.items()])
    #print (url)
    # Lance la requête
    lignes = request_data_cdp(url)

    # Ne retient que les stations comprises dans la liste stations. Pour faciliter les recherches, on passe par les clés des dict
    stations = [oaci for oaci, insee, om in stations]

    # Split la réponse en différentes lignes et range par Station
    if lignes is not None:
        lignes = lignes.split('\n')
        
        for ligne in lignes[1:]: # Evince la première ligne qui est le nombre de lignes de la réponse SA CDP
            ligne = ligne.strip()
            if ligne != str(''):
                oaci = ligne[:4]
                if oaci in stations:
                    reponse.setdefault(oaci, []).append(ligne)
    return reponse

'''def retrieveDatasCDPH(stations = None):
    """ Fonction allant chercher les données CDP H d'une liste de station. 
    La liste représente les tuples (oaci, insee, outremer) des stations. 
    
    Retourne un dictionnaire { oaci: [lignes récupérées] }
    """
    
    reponse = {}
    stations_extract = [ (oaci, insee) for oaci, insee, om in stations if not om]
    reponse.update(retrieveDatasCDPH_metropole(stations_extract))

    stations_extract = [ (oaci, insee) for oaci, insee, om in stations if om]
    reponse.update(retrieveDatasCDPH_om(stations_extract))
    
    return reponse'''

'''def retrieveDatasCDPQ(stations = None):
    """ Fonction allant chercher les données CDP Q d'une liste de station. 
    La liste représente les tuples (oaci, insee, outremer) des stations. 
    
    Retourne un dictionnaire { oaci: [lignes récupérées] }
    """
    reponse = {}

    stations_extract = [ (oaci, insee) for oaci, insee, om in stations if not om]
    reponse.update(retrieveDatasCDPQ_metropole(stations_extract))

    stations_extract = [ (oaci, insee) for oaci, insee, om in stations if om]
    reponse.update(retrieveDatasCDPQ_om(stations_extract))

    return reponse'''

def retrieveDatasCDPH_metropole(stations = None, remote_url = settings.REMOTE_CDPH):
    """ Fonction allant chercher les données CDPH d'une liste de station metropole. 
    La liste représente les tuple (oaci, inseepp) des stations. 
    
    Retourne un dictionnaire { oaci: [lignes récupérées] }

    ex requête: http://nihoa-v27b.meteo.fr/cdp1/h_p?
    &id=384130
    &format=csv
    &meta=id,dvalid,dinsert
    &param=t/10,ff*1.94384,fx*1.94384,w1,preciptotcumfutur(adddate(dvalid,INTERVAL%201%20HOUR),ID,0)/10,preciptotcumfutur(adddate(dvalid,INTERVAL%201%20HOUR),ID,2)/10,preciptotcumfutur(adddate(dvalid,INTERVAL%201%20HOUR),ID,5)/10,preciptotcumfutur(adddate(dvalid,INTERVAL%201%20HOUR),ID,11)/10,preciptotcumfutur(adddate(dvalid,INTERVAL%201%20HOUR),ID,23)/10,EtatSol,pneige/100,dd
    &dpivot=-48,60
    
    """
    reponse = {}
    parametres = {}
    parametres['dpivot'] = "-48,60"  # Permet de faire la demande sur -3h à 48h 
    parametres['format'] = 'csv'    # Réponse du SA CDP en csv 
    parametres['param'] = ','.join([externe for interne, externe in CDPDataHoraire.PARAMETRES_CDPH] )
    parametres['id'] = ",".join([insee for oaci, insee in stations])
    parametres['ordre'] = 'dvalid'
    parametres['meta']=",".join([param for tag, param in CDPDataHoraire.PARAMETRES_METAH]) #"id,dvalid,dinsert"
    
    # Définit l'url : 
    url = remote_url + "&".join([parametre + "=" + value for parametre, value in parametres.items()])
    #print (url)

    # Lance la requête
    lignes = request_data_cdp(url)

    # Etablit les correspondance en oaci et insee de manière à pouvoir indexer le dict par clé oaci
    correspond= {insee:oaci for oaci, insee in stations}

    # Split la réponse en différentes lignes et range par Station
    if lignes is not None:
        lignes = lignes.split('\n')
        for ligne in lignes[1:]: # Evince la première ligne qui est le nombre de lignes de la réponse SA CDP
            ligne = ligne.strip()
            if ligne != str(''):
                insee = ligne[:7]

                oaci = correspond.get(insee, None)

                if oaci is not None:
                    reponse.setdefault(oaci, []).append(ligne)
    
    return reponse

def retrieveDatasCDPH_om(stations = None, remote_url = settings.REMOTE_CDPH_OM):
    """ Fonction allant chercher les données CDPH outre-mer d'une liste de station. 
    La liste représente les tuple (oaci, inseepp) des stations. 
    
    ex requête: http://nihoa-v27b.meteo.fr/cdp1/om_h?dpivot=-48,60&format=csv&param=t/10,ff*1.94384,fx*1.94384,w1,etatsol,rrcum_omfutur(adddate(dvalid,INTERVAL 6 HOUR),ID,0)/10,dd&id=9710101&ordre=dvalid&meta=id,dvalid,dinsert
    
    """
    
    reponse = {}
    parametres = {}
    parametres['dpivot'] = "-48,60"  # Permet de faire la demande sur -3h à 48h 
    parametres['format'] = 'csv'    # Réponse du SA CDP en csv 
    parametres['param'] = ','.join([externe for interne, externe in CDPDataHoraire.PARAMETRES_CDPH_OM])
    parametres['id'] = ",".join([insee for oaci, insee in stations])
    parametres['ordre'] = 'dvalid'
    parametres['meta']=",".join([param for tag, param in CDPDataHoraire.PARAMETRES_METAH]) #"insee,dvalid,dinsert"
    
    # Définit l'url : 
    url = remote_url + "&".join([parametre + "=" + value for parametre, value in parametres.items()])
    #print ("retrieveDatasCDPH_om", url)

    # Lance la requête
    lignes = request_data_cdp(url)

    # Etablit les correspondance en oaci et insee de manière à pouvoir indexer le dict par clé oaci
    correspond= {insee:oaci for oaci, insee in stations}

    # Split la réponse en différentes lignes et range par Station
    if lignes is not None:
        lignes = lignes.split('\n')
        for ligne in lignes[1:]: # Evince la première ligne qui est le nombre de lignes de la réponse SA CDP
            ligne = ligne.strip()
            if ligne != str(''):
                insee = ligne[:7]
                oaci = correspond.get(insee, None)
                if oaci is not None:
                    reponse.setdefault(oaci, []).append(ligne)
    
    return reponse

def retrieveDatasCDPQ_metropole(stations = None, remote_url = settings.REMOTE_CDPQ):
    """ Fonction allant chercher les données CDPQ d'une liste de station. 
    La liste représente les tuple (oaci, inseepp) des stations. 
    
    Retourne un dictionnaire { oaci: [lignes récupérées] }
    
    ex requête: http://nihoa-v27b.meteo.fr/cdp1/om_h?dpivot=-48,60&format=csv&param=t/10,ff*1.94384,fx*1.94384,w1,etatsol,rrcum_omfutur(adddate(dvalid,INTERVAL 6 HOUR),ID,0)/10,dd&id=9710101&ordre=dvalid&meta=id,dvalid,dinsert
    
    """
    PARAMETRES_CDPQ = CDPDataHoraire.PARAMETRES_CDPQ
    reponse = {}
    parametres = {}
    parametres['dpivot'] = "-48,60"  # Permet de faire la demande sur -3h à 48h 
    parametres['format'] = 'csv'    # Réponse du SA CDP en csv 
    parametres['param'] = ','.join(PARAMETRES_CDPQ)
    parametres['id'] = ",".join([insee for oaci, insee in stations])
    parametres['ordre'] = 'dvalid'
    parametres['meta']=",".join([param for tag, param in CDPDataHoraire.PARAMETRES_METAQ]) #"id,dvalid,dinsert"
    
    # Définit l'url : 
    url = remote_url + "&".join([parametre + "=" + value for parametre, value in parametres.items()])
    #print (url)

    # Lance la requête
    lignes = request_data_cdp(url)

    # Etablit les correspondance en oaci et insee de manière à pouvoir indexer le dict par clé oaci
    correspond= {insee:oaci for oaci, insee in stations}

    # Split la réponse en différentes lignes et range par Station
    if lignes is not None:
        lignes = lignes.split('\n')
        for ligne in lignes[1:]: # Evince la première ligne qui est le nombre de lignes de la réponse SA CDP
            ligne = ligne.strip()
            if ligne != str(''):
                insee = ligne[:7]
                oaci = correspond.get(insee, None)
                if oaci is not None:
                    reponse.setdefault(oaci, []).append(ligne)
    
    return reponse

def retrieveDatasCDPQ_om(stations = None, remote_url = settings.REMOTE_CDPQ_OM):
    """ Fonction allant chercher les données CDPQ outre-mer d'une liste de station. 
    La liste représente les tuple (oaci, inseepp) des stations. 
    
    Retourne un dictionnaire { oaci: [lignes récupérées] }

    ex requête: http://nihoa-v27b.meteo.fr/cdp1/om_h?dpivot=-48,60&format=csv&param=t/10,ff*1.94384,fx*1.94384,w1,etatsol,rrcum_omfutur(adddate(dvalid,INTERVAL 6 HOUR),ID,0)/10,dd&id=9710101&ordre=dvalid&meta=id,dvalid,dinsert
    
    """
    PARAMETRES_CDPQ_OM = CDPDataHoraire.PARAMETRES_CDPQ_OM

    reponse = {}
    parametres = {}
    parametres['dpivot'] = "-48,60"  # Permet de faire la demande sur -3h à 48h 
    parametres['format'] = 'csv'    # Réponse du SA CDP en csv 
    parametres['param'] = ','.join(PARAMETRES_CDPQ_OM)
    parametres['id'] = ",".join([insee for oaci, insee in stations])
    parametres['ordre'] = 'dvalid'
    parametres['meta']=",".join([param for tag, param in CDPDataHoraire.PARAMETRES_METAQ_OM]) #"id,dvalid,dinsert"
    
    # Définit l'url : 
    url = remote_url + "&".join([parametre + "=" + value for parametre, value in parametres.items()])
    #print (url)

    # Lance la requête
    lignes = request_data_cdp(url)

    # Etablit les correspondance en oaci et insee de manière à pouvoir indexer le dict par clé oaci
    correspond= {insee:oaci for oaci, insee in stations}

    # Split la réponse en différentes lignes et range par Station
    if lignes is not None:
        lignes = lignes.split('\n')
        for ligne in lignes[1:]: # Evince la première ligne qui est le nombre de lignes de la réponse SA CDP
            ligne = ligne.strip()
            if ligne != str(''):
                insee = ligne[:7]
                oaci = correspond.get(insee, None)
                if oaci is not None:
                    reponse.setdefault(oaci, []).append(ligne)
    
    return reponse

class AeroDataHoraire(object):
    PARAMETRES_CDP_AERO = [
            'idoaci','id','typeprev','dvalid','DateEmissionTAF',
            'visi','visiprob40','VisibiliteTempo','VisibiliteProb40Tempo',
            'ddtaf','DDTAFTempo','DDTAFProb40','DDTAFProb40Tempo',
            'FFTAF','FFTAFTempo','FFTAFProb40','FFTAFProb40Tempo',
            'FXTAF','FXTAFTempo','FXTAFProb40','FXTAFProb40Tempo',
            'wwTAF','wwTAFTempo','wwTAFProb40','wwTAFProb40Tempo'
        ]
    
    FORMAT_DATE_AERO = "%Y-%m-%d %H:%M:%S"

    STATION_SANS_REPORT = ['LFPG', 'LFPO', 'LFLL'] # Stations pour lesquelles il ne faut pas faire poursuivre les becmg, tempo, prob40...

    def __init__(self):
        self.heure_taf = None
        self.echeance = None
        self.ligne = None

    def get_echeance(self):
        """" Retourne l'écheance concernée par cette ligne sous forme d'un datetime """
        return self.echeance

    def get_max_wind(self):
        """ Retourne le vent max (kt) """
        return max(self.FF, self.FX)
    
    def get_mean_wind(self):
        """ Retourne le vent moyen uniquement (kt) """
        return self.FF
    
    def get_wind_dir(self):
        """ Retourne la direction du vent (moyen) """
        return (int(self.DD))

    def get_heure_TAF(self):
        """ Retourne un datetime mentionnant l'heure du TAF à l'origine de cette instance"""
        return self.heure_taf

    def get_donnees_origine(self):
        """ Permet de retourner au contexte la données d'origine. Ici, on va considéder que c'est la ligne du CDP Aéro """
        return self.ligne

    def is_previous(self, dernier):
        """ Retourne True si l'instance passée correspond bien à l'heure passée """
        return self.echeance - timedelta(hours=1) == dernier.echeance

    def decode_temps_present(self, base, tempo, prob40, prob40T, dernier=None): #yves
        """ Decode le temps present de la ligne du cdp aero """
        ww = []
                
        base = base.replace('BECMG','').strip().split(' ')
        tempo = tempo.strip().split(' ')
        prob40 = prob40.strip().split(' ')
        prob40T = prob40T.strip().split(' ')
        
        ww = base
        ww.extend(tempo)
        ww.extend(prob40)
        ww.extend(prob40T)

        # Ajoute les WW du précédent
        if dernier is not None:
            if self.oaci not in self.STATION_SANS_REPORT:
                if self.is_previous(dernier) and dernier.heure_taf == self.heure_taf:
                    # L'objet passé est bien celui qui correspond à l'heure précédente
                    ww.extend(dernier.wwTAFTempo)
                    ww.extend(dernier.wwTAFProb40)
                    ww.extend(dernier.wwTAFProb40Tempo)

        # Enleve les doublons
        reponse = sorted(list(set(ww))) 
        
        # Enlève les entrées nulles
        ww = [ s for s in reponse if s != '']

        if len(reponse) > 1 : 
            # Enlève les No Significant Weather si plusieurs temps présents
            ww = [ s for s in ww if s != 'NSW']
            
        return ww, base, tempo, prob40, prob40T

    def decode_bloc_visi(self, VV):
        """ Décode un bloc de visibilité et retourne un tableau avec les visibilités décrites """
        sVV = VV.strip()
        base = []

        if len(sVV)>4:
            # Presence d'un groupe avec variation
            base = [sVV[:-4], sVV[-4:] ]
        else:
            if sVV != '':
                base = [sVV]
        return base

    def decode_visibilite(self, base, tempo, prob40, prob40T, dernier=None):
        """ Retourne  ( visi moyene min, visi moyenne max, [visi du tempo],[visi du 40],[visi] """
        VV = []

        base = self.decode_bloc_visi(base)
        tempo = self.decode_bloc_visi(tempo) 
        prob40 = self.decode_bloc_visi(prob40) 
        prob40T = self.decode_bloc_visi(prob40T) 

        VV = base
        VV.extend(tempo)
        VV.extend(prob40)
        VV.extend(prob40T)
        
        # Ajoute les WW du précédent
        if dernier is not None:
            if self.oaci not in self.STATION_SANS_REPORT:
                if self.is_previous(dernier) and dernier.heure_taf == self.heure_taf:
                    # L'objet passé est bien celui qui correspond à l'heure précédente
                    # Mais on ne reporte que si issu du même TAF
                    VV.extend(dernier.VisibiliteTempo)
                    VV.extend(dernier.visiprob40)
                    VV.extend(dernier.VisibiliteProb40Tempo)

        # Parcourt la liste de toutes les visi pour convertir en entier
        reponse = []
        for visi in VV:
            try:
                visi = int(visi)
                if visi >= 9999:
                    visi = 10000
                reponse.append(visi)
            except:
                pass
                    
        if not reponse:
            # Pas de visibilite significative (CAVOK ?), on affecte le max
            reponse.append(10000)
            reponse.append(10000)
        
        if len(reponse) == 1:
            # Une seule valeur, le max est fixe a 10000
            reponse.append(10000)
        
        reponse = sorted(reponse)
        vmin, vmax = reponse[0], reponse[-1] # Definit le min et max

        # Assure la coherence en cas d'occurrence de brouillard
        #TODO: ajouter la réduction de visi selon le temps présent

        if self.occurrence_brouillard():
            if vmin>1000:
                vmin = 1000
            if vmax>5000:
                vmax= 5000
        # Assure la coherence en cas d'occurrence de brume
        if self.occurrence_brume():
            if vmin>5000:
                vmin = 5000
            if vmax<5000:
                vmax= 5000
        
        return vmin, vmax, VV, base, tempo, prob40, prob40T

    def decode_param_supp(self):
        """ Recherche certains parametres dans les temps presents du taf 
            Met à jour directement la liste des temps présents de l'instance
        """
        temps_present = ('TS','GR','SQ','FG','FZFG','FZRA','FZDZ','SN', 'GS')
         
        wc = []
        if  self.WW == ['NSW']:
            # Pas de parametre utile, on retourne du vide
            return None
        
        for ww in self.WW:
            if ww in ['MIFG', 'BCFG', 'PRFG']:
                # Exclue ces temps presents de la recherche des parametres significatifs
                continue
            for t in temps_present:
                # Si l'un des temps present du taf est dans la liste temps_present, on met celui-ci
                # dans la liste des parametres complementaires 
                if t in ww:
                    if t == 'GR':
                        wc.append('GS') # Si on a de la grele dans le TAF, on ajoute automatiquement du grain
                    if t=='FZFG':
                        wc.append('FG') # Si on a du brouillard givrant dans le TAF, on ajoute automatiquement du brouillard
                    wc.append(t)

        if wc:
            self.WW.extend(wc)
            self.WW = list(set(self.WW))
        return wc

    def get_WW(self):
        """ Retourne la liste des temps présents d'une échéance de manière ordonnée """
        return sorted(self.WW)

    def occurrence_brume(self):
        """ Retourne True si BR fait partie des temps presents """
        return 'BR' in self.WW
    
    def occurrence_brouillard(self):
        """ Retourne True si BR fait partie des temps presents complémentaires"""
        return 'FG' in self.WW
    
    def occurrence_brouillard_dense(self):
        """ Retourne True si l'échéance présente un brouillard ET que la visibilité min est <= 200 """
        return self.occurrence_brouillard() and self.VVmin <= 200
    
    def decode_force_vent_max(self, dernier=None):
            """ Permet d'extraire les vents maxi et d'en extraire la force la plus elevee"""
            vents = []
            
            for fx in [self.FXTAFTempo, self.FXTAFProb40,self.FXTAFProb40Tempo]:
                vents.append(fx)

            # Ajoute les FFX du précédent
            if dernier is not None:
                if self.oaci not in self.STATION_SANS_REPORT:
                    if self.is_previous(dernier) and dernier.heure_taf == self.heure_taf:
                        # L'objet passé est bien celui qui correspond à l'heure précédente
                        # Mais on ne report que si issu du même taf
                        if dernier.__dict__.get('BECMG_FX', None) is not None:
                            vents.append(dernier.__dict__.get('BECMG_FX'))
                        vents.append(dernier.FXTAFTempo)
                        vents.append(dernier.FXTAFProb40)
                        vents.append(dernier.FXTAFProb40Tempo)

            # Recherche un becmg (plus de 3 caracteres dans le premier champ) pour le spliter et le traiter en deux temps
            self.FXTAF = self.FXTAF.strip()
            if len(self.FXTAF) > 3: # On trouve du becmg
                vents.append(self.FXTAF[-3:])
                self.BECMG_FX = self.FXTAF[-3:]
                vents.append(self.FXTAF[:-3])
            else:
                vents.append(self.FXTAF)

            # Parcourt la liste pour trouver la force maxi
            FXmax = -1
            #print (vents)
            for v in vents:
                try:
                    if v == 'P99': # Vent superieur a 100 noeuds
                        v='100'
                                
                    v= int(v)
                    
                    if v == 999: # Vent variable, on laisse tomber
                        continue
                    
                    if v > FXmax:
                        FXmax = v 
                except:
                    pass
                
            if FXmax == -1:
                return None
            
            return FXmax

    def decode_force_vent_moyen(self, dernier): 
            """ Permet d'extraire les vents moyen d'un ensemble de chaines et d'en tirer le max de meme que la direction de ce vent max"""

            direction_max = None
            maxi = -1
            
            vents = []
            
            # Associe les forces de vent et les directions correspondant dans un meme tuple
            vents.append( ( self.FFTAFTempo, self.DDTAFTempo) )
            vents.append( ( self.FFTAFProb40, self.DDTAFProb40) )
            vents.append( ( self.FFTAFProb40Tempo, self.DDTAFProb40Tempo) )

            # Ajoute les FFX du précédent
            if dernier is not None:
                if self.oaci not in self.STATION_SANS_REPORT:
                    if self.is_previous(dernier) and dernier.heure_taf == self.heure_taf:
                        # L'objet passé est bien celui qui correspond à l'heure précédente
                        # Mais on ne report que si issu du même taf
                        if dernier.__dict__.get('BECMG_FF', None) is not None:
                            vents.extend(dernier.__dict__.get('BECMG_FF'))
                        vents.extend( [( dernier.FFTAFProb40, dernier.DDTAFProb40 )] )
                        vents.extend( [( dernier.FFTAFTempo, dernier.DDTAFTempo )] )
                        vents.extend( [( dernier.FFTAFProb40Tempo, dernier.DDTAFProb40Tempo )] )

            # Dans le premier element du tableau, il peut y avoir un codage de becoming (plus de 3 caracteres)
            # Si c'est le cas, on split pour le traiter en deux fois
            self.FFTAF = self.FFTAF.strip()
            if len(self.FFTAF) > 3: 
                # On disseque la valeur en deux
                vents.append( (self.FFTAF[-3:], self.ddtaf[-3:])) 
                self.BECMG_FF = [(self.FFTAF[-3:], self.ddtaf[-3:])]
                vents.append( (self.FFTAF[:-3],self.ddtaf[:-3]) )
            else:
                vents.append( (self.FFTAF, self.ddtaf)) 

            # Parcourt les vent pour trouver le maxi
            for ff, dd in vents:
                try:
                    ff = ff.strip()
                    dd = dd.strip()
                        
                    # Cas du vent superieur a 99 kt
                    if ff == 'P99':
                        ff='100'
                        
                    ff = int(ff)
                    dd = int(dd)
                    
                    if ff > maxi:
                        maxi = ff
                        direction_max = dd
                    
                except:
                    pass
                
            if maxi == -1:
                return None, None
            
            return maxi, direction_max

    def decode_vent(self, dernier=None): #yves
            """
                Decode la partie d'une ligne TAF qui concerne le vent pour retourner:
                vent_moy, vent_max, dd_moy et les tempo pour l'echeance suivante
            """
            
            # Decode le vent moyen
            vent_moy, dd_moy = self.decode_force_vent_moyen(dernier)
            
            # Decode le vent maxi
            vent_max = self.decode_force_vent_max(dernier)

            # Vérifie la cohérence min-max
            if (vent_moy is not None):
                if vent_max is None:
                    vent_max = vent_moy

                if vent_moy > vent_max:
                    vent_max = vent_moy          
            
            return vent_moy, vent_max, dd_moy

    def load_from_cdp_aero(self, ligne, dernier=None):
        """ Charge les données contenues dans une ligne du cdp, donc une échéance """

        """"'visi','visiprob40','VisibiliteTempo','VisibiliteProb40Tempo',
            'ddtaf','DDTAFTempo','DDTAFProb40','DDTAFProb40Tempo',
            'FFTAF','FFTAFTempo','FFTAFProb40','FFTAFProb40Tempo',
            'FXTAF','FXTAFTempo','FXTAFProb40','FXTAFProb40Tempo',
            'wwTAF','wwTAFTempo','wwTAFProb40','wwTAFProb40Tempo'"""
        try:
            parametres = {}
            self.ligne = ligne
            

            infos = ligne.split(';')
            for index, val in enumerate(infos[:-1]):
                parametres[self.PARAMETRES_CDP_AERO[index]] = val.strip()

            self.oaci = parametres['idoaci']

            self.heure_taf = dt.strptime(parametres['DateEmissionTAF'], self.FORMAT_DATE_AERO)
            self.echeance = dt.strptime(parametres['dvalid'], self.FORMAT_DATE_AERO)
            
            if parametres['wwTAF'].strip() == 'CNL':
                # Le TAF est annulé, les infos seront inexploitable, on skip
                return None

            if self.echeance.minute != 0:
                # Prévi intermédiaire, ne concerne pas le TAF
                return None

            # On utilise un système de tuple pour faire la correspondance entre le nom des
            # paramètres récupérés du cdp aero et ceux qu'on veut donner en interne
            # Si on doit changer de source de données, garder malgré tout ces noms internes
            trans = [ ('wwTAF','wwTAF'),('wwTAFTempo','wwTAFTempo'),('wwTAFProb40','wwTAFProb40'),('wwTAFProb40Tempo','wwTAFProb40Tempo')]
            for interne, cdp in trans:
                #TODO: transcrire en liste de temps présent
                self.__dict__[interne] = parametres[cdp]


            trans = [ ('ddtaf','ddtaf'),('DDTAFTempo','DDTAFTempo'),('DDTAFProb40','DDTAFProb40'),('DDTAFProb40Tempo','DDTAFProb40Tempo'),]
            for interne, cdp in trans:
                self.__dict__[interne] = parametres[cdp]

            trans = [ ('FFTAF','FFTAF'),('FFTAFTempo','FFTAFTempo'),('FFTAFProb40','FFTAFProb40'),('FFTAFProb40Tempo','FFTAFProb40Tempo'),
                    ('FXTAF','FXTAF'),('FXTAFTempo','FXTAFTempo'),('FXTAFProb40','FXTAFProb40'),('FXTAFProb40Tempo','FXTAFProb40Tempo'),]
            for interne, cdp in trans:
                self.__dict__[interne] = parametres[cdp]
            
            trans = [ ('visi','visi'),('visiprob40','visiprob40'),('VisibiliteTempo','VisibiliteTempo'),('VisibiliteProb40Tempo','VisibiliteProb40Tempo'),]
            for interne, cdp in trans:
                self.__dict__[interne] = parametres[cdp]
            
            # Décode les infos pour les rendres exploitable

            # Decode le temps present
            self.WW, self.wwTAF, self.wwTAFTempo, self.wwTAFProb40, self.wwTAFProb40Tempo = \
                self.decode_temps_present(self.wwTAF, self.wwTAFTempo, self.wwTAFProb40, self.wwTAFProb40Tempo, dernier)
            
            # Vérifie la présence de paramètres supplémentaires
            reponse = self.decode_param_supp()
            
            # Decode la visibilité
            self.VVmin, self.VVmax, self.VV, self.visi, self.VisibiliteTempo, self.visiprob40, self.VisibiliteProb40Tempo = \
                self.decode_visibilite(self.visi, self.VisibiliteTempo, self.visiprob40, self.VisibiliteProb40Tempo, dernier)
            
            # Decode le vent
            self.FF, self.FX, self.DD = self.decode_vent( dernier)
            
            self.FF = int(ceil(float(self.FF)))
            self.FX = int(max(self.FF,ceil(float(self.FX))))
            self.DD = int(self.DD)

            #TODO: Rédiger des TU sur les occurrences de brouillard et de brume réduisant la visibilité
            if self.occurrence_brume():
                self.visi_min = 1000
                self.visi_max = 5000
            if self.occurrence_brouillard():
                self.visi_min = 0
                self.visi_max = 1000

            #TODO: voir s'il faut faire quelque chose pour le potentiel de neige et l'état du sol
            
        except Exception as e:
            print(e)
            return None

        return self

class AeroDataStation(object):
    """ Stoque les données aéro horaires d'une station """
    def __init__(self, lignes):
        self.echeances = {} # {echeance : AeroDataHoraire }
        
        # Trie la liste pour avoir les échéances dans l'ordre chronologique
        lignes = sorted(lignes)

        dernier_objet = None
        for ligne in lignes:
            decode = AeroDataHoraire().load_from_cdp_aero(ligne, dernier_objet)

            if decode is not None:
                dernier_objet = decode     
                self.echeances[decode.echeance] = decode

    def get_echeance(self, dt):
        return self.echeances.get(dt,None)
    
    @property
    def ordered_echeances(self):
        return sorted(self.echeances.keys())

    def get_echeances(self):
        ''' Retourne un tableau des data avec les echeances triées chronologiquement'''
        ech = sorted(self.echeances.keys())
        return [ self.echeances[key] for key in ech]

class AeroDataStations(object):
    """ Stoque les données aéro horaires de toutes les stations """
    def __init__(self):
        self.stations = {} # {oaci: AeroDataStation}

    def load_datas(self, conteneur):
        """ Charge les données récupérées via le WS 
            conteneur est de la forme { oaci: [lignes str] }

            Retourne None
        """
        for oaci, liste in conteneur.items():
            self.stations[oaci] = AeroDataStation(liste)

    def getStation(self, oaci):
        """ Retourne le conteneur de données d'une station particulière oaci"""
        return self.stations.get(oaci, None)

class CDPDataHoraire(object):
    PARAMETRES_CDPH = [
    
    ('t','t/10'),('ff','ff*1.94384'),('fx','fx*1.94384'),('ww','w1'),
    ('rr1','preciptotcumfutur(adddate(dvalid,INTERVAL%201%20HOUR),ID,0)/10'),
    ('rr3','preciptotcumfutur(adddate(dvalid,INTERVAL%201%20HOUR),ID,2)/10'),
    ('rr6','preciptotcumfutur(adddate(dvalid,INTERVAL%201%20HOUR),ID,5)/10'),
    ('rr12','preciptotcumfutur(adddate(dvalid,INTERVAL%201%20HOUR),ID,11)/10'),
    ('rr24','preciptotcumfutur(adddate(dvalid,INTERVAL%201%20HOUR),ID,23)/10'),
    ('etatsol', 'EtatSol'),('pneige','pneige/100'),('dd','dd')]
    
    PARAMETRES_CDPH_OM = [('t','t/10'),('ff','ff*1.94384'),('fx','fx*1.94384'),('ww','w1'),('etatsol','etatsol'),
                        ('rr6','rrcum_omfutur(adddate(dvalid,INTERVAL 6 HOUR),ID,0)/10'),('dd','dd')]

    PARAMETRES_CDPQ_OM = ['tn/10','tx/10']

    PARAMETRES_CDPQ = ['tn/10','tx/10']

    PARAMETRES_METAQ = [('id','id'), ('dvalid','dvalid'), ('dinsert','dinsert')]
    PARAMETRES_METAQ_OM = [('id','id'), ('dvalid','dvalid'), ('dinsert','dinsert')]
    
    PARAMETRES_METAH = [('id','id'), ('dvalid','dvalid'), ('dinsert','dinsert')]

    FORMAT_DATE = "%Y-%m-%d %H:%M:%S"

    def __init__(self, outremer):
        self.outremer = outremer
        self.echeance = None
        self.ligne = None

    @staticmethod
    def get_entetes_requete(genre_parametre):
        """ Permet de retourner la liste des entetes de colonne requetées aux CDP """
        if genre_parametre == CDPDataHoraire.PARAMETRES_CDPQ_OM: 
            data = [tag for tag, param in CDPDataHoraire.PARAMETRES_METAQ_OM]
            data.extend(genre_parametre)
            return data
        elif genre_parametre == CDPDataHoraire.PARAMETRES_CDPQ:
            data = [tag for tag, param in CDPDataHoraire.PARAMETRES_METAQ]
            data.extend(genre_parametre)
            return data
        if genre_parametre in [CDPDataHoraire.PARAMETRES_CDPH, CDPDataHoraire.PARAMETRES_CDPH_OM]:
            data = []
            data.extend(CDPDataHoraire.PARAMETRES_METAH)
            data.extend(genre_parametre)
            return [tag for tag, champ in data]
        return []
        
    def get_donnees_origine(self):
        """ Permet de retourner au contexte la données d'origine. Ici, on va considéder que c'est la ligne du CDP H"""
        return self.ligne

    def get_param(self, param):
        """ Retourne le paramètre convertit selon le type attendu.
            Si non trouvé, retourne None
        """
        try:
            if param in ['t', 'tn_extreme', 'tx_extreme', 'rr1', 'rr3', 'rr6', 'rr12', 'rr24','pneige']:
                return float(self.__dict__[param])
            if param in ['ff', 'fx', 'etatsol', 'dd']:
                return int(self.__dict__[param]) 
            return self.__dict__[param]
        except:
            return None
    
    def set_T_Extreme(self, T, nom_param):
        """ Lors de la ventillation des données Q, si on trouve une extreme sur cette heure, 
            On lui affecte la température ext quotidienne
        """
        self.__dict__[nom_param] = T

    def get_WW(self):
        return self.get_param('ww')

    def get_max_wind(self):
        """ Retourne le vent max (kt) """
        return max(self.get_param('ff'), self.get_param('fx'))

    def get_mean_wind(self):
        """ Retourne le vent moyen uniquement (kt) """
        return self.get_param('ff')
        
    def get_wind_dir(self):
        """ Retourne la direction du vent """
        return self.dd

    def occurrence_brume(self):
        """ Retourne True si BR fait partie des temps presents """
        return 'BR' in self.ww
    
    def occurrence_brouillard(self):
        """ Retourne True si BR fait partie des temps presents complémentaires"""
        return 'FG' in self.ww
    
    def occurrence_brouillard_dense(self):
        """ Retourne toujours False car on ne doit pas générer de DENSE_FG à partir du CDP H"""
        return False

    def decode_temps_present(self):
        """ A partir du code synop, déduit une liste de temps présent type aéronautique """
        temps = {
                    'SN': ['13','16','17','21','22','38','74'],
                    'RA': ['9','10','11','12','14','18','19','20','27','29','30','32','40','41','42','43','44','46','64','65','66'],
                    'FZRA': ['8'],
                    'FZFG': ['4', '5', '6'],
                    'FG': ['1', '2', '3', '4', '5', '6', '33'],
                    'GR': ['23','28', '29'],
                    'TS': ['24', '25', '26', '27', '28', '29', '30', '31', '32']

        }
        if self.outremer:
            temps = {
                    'FG': ['1','3','54','64','65','66','74'],
                    'FZFG': ['5'],
                    'FZRA': ['8','36'],
                    'SN': ['13','16','17','21','22','38','74'],
                    'GR': ['23','26'],
                    'RA': ['9','10','11','12','14','18','19','20','27','29','30','32','40','41','42','43','44','46','64','65','66'],
                    'TS': ['12', '24','25','26','27','28','29']
                }

        trouve = []
        for cle, tabl in temps.items():
            if self.ww in tabl:
                trouve.append(cle)
        
        if not trouve:
            # Pas de temps significatif, on retourne a minima NSW
            trouve.append('NSW')
            
        self.ww = list(set(trouve)) 

    def decode_param_supp_cdp(self):
        """ Permet d'ajouter certains paramètres en fonction d'autres trouvés dans la liste """ 
        temps_present = ('TS','GR','SQ','FG','FZFG','FZRA','FZDZ','SN', 'GS')
        
        wc = []
        
        for ww in self.ww:
            for t in temps_present:
                # Si l'un des temps present du taf est dans la liste temps_present, on met celui-ci
                # dans la liste des parametres complementaires 
                if t in ww:
                    if t == 'GR':
                        wc.append('GS') # Si on a de la grele dans le TAF, on ajoute automatiquement du grain
                    if t=='FZFG':
                        wc.append('FG') # Si on a du brouillard givrant dans le TAF, on ajoute automatiquement du brouillard
                    wc.append(t)

        return wc

    def copy_this_hour(self, echeance):
        """ Permet de duppliquer cette instance sur une nouvelle instance de CDPDataHoraire qui est retournée """
        nouvelle = CDPDataHoraire(self.outremer)
        for key, value in self.__dict__.items():
            nouvelle.__dict__[key] = value
        nouvelle.echeance = echeance
        return nouvelle
    
    def __str__(self):
        """ A des fins de bug essentiellement, affiche une synthèse des données de cette heure """
        chaine = []
        exclure = ['ligne', 'dprod', 'outremer']
        for key, value in self.__dict__.items():
            if key not in exclure:
                chaine.append(key+":"+ str(value))
        
        return " -".join(chaine)

    def load_from_cdp_h(self, ligne, dernier=None):
        """ Charge les données contenues dans une ligne du cdp, donc une échéance """

        try:
            self.ligne = ligne

            definition_parametres = []
            definition_parametres.extend(CDPDataHoraire.PARAMETRES_METAH)
            
            if self.outremer:
                definition_parametres.extend(self.PARAMETRES_CDPH_OM)
            else:
                definition_parametres.extend(self.PARAMETRES_CDPH)

            infos = ligne.split(';')
            for index, val in enumerate(infos[:-1]):    
                # Charge la valeur dans la variable de l'instance qui prend le nom interne
                self.__dict__[definition_parametres[index][0]] = val.strip()
            self.insee = self.id     

            #print(self.__dict__)

            self.echeance = dt.strptime(self.dvalid, self.FORMAT_DATE)

            if self.echeance.minute != 0:
                # Ne garde que les échéances horaires pleines
                return None

            # Format les présents présents
            self.decode_temps_present() 
            
            self.ww.extend(self.decode_param_supp_cdp())
            self.ww = list(set(self.ww))

            # Arrondi les vents
            self.ff = int(ceil(float(self.ff)))
            if self.fx is None:
                self.fx = self.ff
            self.fx = int(max(self.ff,ceil(float(self.fx))))
            if self.dd is not None:
                self.dd = int(self.dd)

            if self.occurrence_brume():
                self.visi_min = 1000
                self.visi_max = 5000
            if self.occurrence_brouillard():
                self.visi_min = 0
                self.visi_max = 1000

        except Exception as e:
            print(e)
            return None

        return self

class CDPDataStation(object):
    """ Stoque les données CDP horaires d'une station """
    def __init__(self, lignes, outremer):
        self.echeances = {} # {echeance : CDPDataHoraire }
        self.insee = None

        # Trie la liste pour avoir les échéances dans l'ordre chronologique
        lignes = sorted(lignes)

        dernier_objet = None
        for ligne in lignes:
            decode = CDPDataHoraire(outremer).load_from_cdp_h(ligne)
            #print("ligne", ligne)
            #print("decode", decode)
            if decode is not None:
                dernier_objet = decode     
                self.echeances[decode.echeance] = decode
                self.insee = decode.insee

        # Après avoir chargé les données d'une station, si celle-ci est outre-mer, 
        if outremer:
            # Il faut comlber les trous sexti-horaire en duppliquant la données
            self.dupplication()

            # il faut reconstituer les cumuls rr3, rr6, rr12 et rr24
            self.ventille_RR()

    def affiche_donnees_station(self):
        """ A des fins de bug essentiellement, permet d'afficher les données contenues ce conteneur
        ordonné par dates croissantes """
        echeances = self.ordered_echeances
        for echeance in echeances:
            data = self.get_echeance(echeance)
            print(data)
            
    def get_echeance(self, dt):
        return self.echeances.get(dt, None)

    def dupplication(self):
        """ Comme les données outre-mer sont toutes les 6 heures, on va chercher à 
        duppliquer les infos sur les 5 heures restantes pour combler les trous """
        heures_dispo = self.ordered_echeances
        for heure in heures_dispo:
            # Pour chaque échéance existante, on comble les 5 heures suivantes avec les mêmes données
            data = self.get_echeance(heure)
            data.rr1 = float(data.rr6)/6
            del(data.__dict__['rr6'])
            
            for i in range(1,6):
                new_echeance = heure + timedelta(hours=i)    
                new_data = data.copy_this_hour(new_echeance)
                if new_data is not None:
                    self.echeances[new_echeance] = new_data

    def ventille_RR(self):
        """ Permet de réconstituer les cumuls de pluie RR3, 6, 12 et 24h à partir 
        des RR1 pour les stations outremer. 
        
        Les valeurs sont ensuite arrondies : self.rr24 = round(float(rr24),2)
        """

        a_balayer = self.ordered_echeances
        for echeance in a_balayer:
            # Pour chacune des échéances, on cherche à consituer le lot des échéances pour les cumuls
            for ind in [3, 6, 12, 24]:
                variable = 'rr'+str(ind)
                heures = [ echeance + timedelta(hours=i ) for i in range(0,ind)]
                datas = []
                cumul = 0
                
                for heure in heures:
                    data_heure = self.get_echeance(heure)
                    if data_heure is None:
                        continue

                    rr1 = data_heure.get_param('rr1')
                    if rr1 is None:
                        continue
                    cumul = cumul + data_heure.get_param('rr1')
                    datas.append(data_heure)

                if len(datas) == len(heures):
                    # On dispose des données de toute la série, on peut prendre en compte le cumul
                    datas[0].__dict__[variable] = round(float(cumul),2)
            
            # Après ventillation, profite pour arrondir le RR1
            horaire = self.get_echeance(echeance)
            horaire.rr1 = round(float(horaire.get_param('rr1')),2)
                    
    @property
    def ordered_echeances(self):
        return sorted(self.echeances.keys())

    def get_echeances(self):
        ''' Retourne un tableau des data avec les echeances triées chronologiquement'''
        ech = sorted(self.echeances.keys())
        return [ self.echeances[key] for key in ech]

    def define_plage_dates_tn(self, jour):
        """ Definit a paartir du code insee d'une station et de la date d'un extremum, 
            la liste des heures sur lesquelles l'extremum doit se produire """

        indicatif = self.insee[:3]
        date_pivot = jour
        reponse = []
        
        if indicatif in ['971', '972']: # Antilles
            date_min = date_pivot
            #date_max = date_pivot + timedelta(hours= 23)

        elif indicatif in ['9714', '985']: # Reunion, Mayotte
            date_min = date_pivot - timedelta(hours= 9)
            #date_max = date_pivot + timedelta(hours= 14)
            
        elif indicatif == '973': # Guyane 
            date_min = date_pivot - timedelta(hours= 3)
            #date_max = date_pivot + timedelta(hours= 20)
            
        elif indicatif == '987': # DIRPF 
            date_min = date_pivot + timedelta(hours= 6)
            #date_max = date_pivot + timedelta(hours= 29)
            
        elif indicatif == '988': # Nouvelle-Calédonie 
            date_min = date_pivot - timedelta(hours= 11)
            #date_max = date_pivot + timedelta(hours= 12)
            
        elif indicatif == '986': # W et F
            date_min = date_pivot - timedelta(hours= 12)
            #date_max = date_pivot + timedelta(hours= 11)
            
        elif indicatif == '975': # SPM
            date_min = date_pivot - timedelta(hours= 3)
            #date_max = date_pivot + timedelta(hours= 20)
            
        else: # Metropole
            date_min = date_pivot - timedelta(hours= 6)
            #date_max = date_pivot + timedelta(hours= 17)
            
        for i in range(0,24): # Etablit la liste des heures comprises entre les dates min et max
            reponse.append(date_min + timedelta(hours=i))
            
        return reponse

    def define_plage_dates_tx(self, jour):
        """ Definit a partir du code insee d'une station et de la date d'un extremum, 
            la liste des heures sur lesquelles l'extremum doit se produire """

        indicatif = self.insee[:3]
        date_pivot = jour 
        reponse = []
        
        if indicatif in ['971', '972']: # Antilles
            date_min = date_pivot + timedelta(hours= 12)
            #date_max = date_pivot + timedelta(hours= 23)

        elif indicatif in ['9714', '985']: # Reunion, Mayotte
            date_min = date_pivot + timedelta(hours= 3)
            #date_max = date_pivot + timedelta(hours= 14)
            
        elif indicatif == '973': # Guyane 
            date_min = date_pivot + timedelta(hours= 9)
            #date_max = date_pivot + timedelta(hours= 20)
            
        elif indicatif == '987': # DIRPF 
            date_min = date_pivot + timedelta(hours= 18)
            #date_max = date_pivot + timedelta(hours= 29)
            
        elif indicatif == '988': # Nouvelle-Calédonie 
            date_min = date_pivot - timedelta(hours= 11)
            #date_max = date_pivot + timedelta(hours= 12)
            
        elif indicatif == '986': # W et F
            date_min = date_pivot - timedelta(hours= 12)
            #date_max = date_pivot + timedelta(hours= 11)
            
        elif indicatif == '975': # SPM
            date_min = date_pivot + timedelta(hours= 9)
            #date_max = date_pivot + timedelta(hours= 20)
            
        else: # Metropole
            date_min = date_pivot + timedelta(hours= 6)
            #date_max = date_pivot + timedelta(hours= 17)
            
        for i in range(0,24): # Etablit la liste des heures comprises entre les dates min et max
            reponse.append(date_min + timedelta(hours=i))
            
        return reponse

    def ventille_Tn(self, Tn, date):
        """ Permet de mettre la température extrème d'une journée sur la ligne horaire la plus probable """

        # Determine la liste des heures de cette plage (variable selon la zone de la station outre-mer)
        les_heures = self.define_plage_dates_tn(date)
     
        # Definit la temperature minimale parmi la plage horaire pour y affecter la temperature minimale quotidienne
        tn = 2000
        heure_tn = None
        for l_heure in les_heures:
            if l_heure is not None:
                ligne_cdp = self.get_echeance(l_heure)
                if ligne_cdp is None:
                    # On n'a pas toute la série de donnée, une extrapolation de l'heure extreme serait idiote
                    return 
                t = ligne_cdp.get_param('t')
                if t is not None and t <= tn:
                    tn = t
                    heure_tn = l_heure
                
        if heure_tn is not None:
            ligne_cdp = self.get_echeance(heure_tn)
            ligne_cdp.set_T_Extreme(Tn, 'tn_extreme')


    def ventille_Tx(self, Tx, date):
        """ Permet de mettre la température extrème d'une journée sur la ligne horaire la plus probable """
        # Determine la liste des heures de cette plage (variable selon la zone de la station outre-mer)
        les_heures = self.define_plage_dates_tx(date)
     
        # Definit la temperature minimale parmi la plage horaire pour y affecter la temperature minimale quotidienne
        tx = -2000
        heure_tx = None
        for l_heure in les_heures:
            if l_heure is not None:
                ligne_cdp = self.get_echeance(l_heure)
                if ligne_cdp is None:
                    # On n'a pas toute la série de donnée, une extrapolation de l'heure extreme serait idiote
                    return 
                t = ligne_cdp.get_param('t')
                if t is not None and t >= tx:
                    tx = t
                    heure_tx = l_heure
                
        if heure_tx is not None:
            ligne_cdp = self.get_echeance(heure_tx)
            ligne_cdp.set_T_Extreme(Tx, 'tx_extreme')

class CDPDataStations(object):
    """ Stoque les données CDP H/Q horaires de toutes les stations """
    def __init__(self):
        self.stations = {} # {oaci: CDPDataStation}

    def load_datas(self, conteneur, outremer):
        """ Charge les données récupérées via le WS 
            conteneur est de la forme { oaci: [lignes str] }

            Retourne None
        """
        for oaci, liste in conteneur.items():
            self.stations[oaci] = CDPDataStation(liste, outremer)

    def load_daily_datas(self, donneeQ, conteneur, outermer):
        """ Cette fonction a pour but d'assimiler un conteneur donneeQ de données quotidiennes 

            Cela permet de rectifier les données de température en fonction des Tn/Tx
            Ici le donneeQ est une instance {oaci: [lignes du ficjier cdpq]}
            Dans le fichier cdpq, les échéances sont à 00TU. La période concernée par cette date dépend de la zone considérée

            Les données ne sont pas stockées dans un nouveau conteneur mais directement traitées pour être ventillées dans les conteneurs data
        """
        for oaci, liste_lignes in donneeQ.items():
            data = conteneur.getStation(oaci)
            if data is not None:
                for ligne in liste_lignes:
                    infos = ligne.split(";") 
                    jour = dt.strptime(infos[1], '%Y-%m-%d %H:%M:%S')       
                    tn = float(infos[3])
                    data.ventille_Tn(tn, jour)
                    tx = float(infos[4])
                    data.ventille_Tx(tx, jour)

    def getStation(self, oaci):
        """ Retourne le conteneur de données d'une station particulière oaci"""
        return self.stations.get(oaci, None)
    
    def getStations(self):
        """ Retourne le contenu du conteneur sous forme de dictionnaire identique à self.stations """
        return self.stations

class ManagerData(object):
    """ Cette classe a pour but de prendre en charge l'ensemble des données Aéro et CDP.
        Depuis l'extérieur, cela permet de ne pas se soucier de l'emplacement des données et le format.
        Elle encapsule notamment les fonctions "declenche" qui testent si sur une heure données, on a un test déclenchant
        pour un type de maa donné
    """
    def __init__(self, data_aero, data_cdph):
        """ Initialise la classe avece les conteneurs de base """
        self.aero = data_aero # instance de AeroDataStations
        self.cdp = data_cdph # instance de CDPDataStations

    def questionne_cdp(self, oaci, echeance, type_maa, seuil=None):
        """ Pour le descryptif, voir question_declenche
            Cette fonction retourne la même chose avec en plus la date d'émission du TAF si c'est bien le 
            TAF qui en est à l'origine, ou None sinon
        """
        origine = None # Permet de déterminer si cela provient du TAF
        data = None
        if seuil == '': seuil = None

        # Certains MAA ne sont pas gérables par les CDP Aéro. Donc pur ceux-là, pas la peine de carger la données aéro
        zappe = ['TMIN', 'TMAX', 'RR1', 'RR3', 'RR6', 'RR12', 'RR24']
        if type_maa not in zappe:
            data = self.aero.getStation(oaci)
            if data is not None:
                data = data.get_echeance(echeance)

        if data is not None:
            # A trouvé la station et l'échéance. Donc c'est elle qui doit retourner l'info.
            origine = data.get_heure_TAF()
        else:
            # Le test sera fait par le cdp h/q
            data = self.cdp.getStation(oaci)
            if data is not None:
                data = data.get_echeance(echeance)

        if data is not None: # Pas trouvé cette data
            # On a le conteneur en main, on peut faire lancer le test 
            #TODO: on doit pouvoir définir ces évalutations dans les objets AutorisedMAA pour plus d'encapsulation
            try:   
                if type_maa == 'VENT':
                    return seuil <= data.get_max_wind(), origine
                if type_maa == 'VENT_MOY':
                    return seuil <= data.get_mean_wind(), origine
                if type_maa == 'TMIN':
                    Tretenue = data.get_param('t')
                    Textreme = data.get_param('tn_extreme')
                    if Textreme is not None:
                        Tretenue = min(Tretenue, Textreme)
                    return seuil >= Tretenue, origine
                if type_maa == 'TMAX':
                    Tretenue = data.get_param('t')
                    Textreme = data.get_param('tx_extreme')
                    if Textreme is not None:
                        Tretenue = max(Tretenue, Textreme)
                    return seuil <= Tretenue, origine
                if type_maa in ['RR1', 'RR3', 'RR6', 'RR12', 'RR24']:
                    return seuil <= data.get_param(type_maa.lower()), origine
                if type_maa in ['TS','GR', 'SQ', 'FG', 'FZFG', 'FZRA', 'FZDZ']:
                    return type_maa in data.get_WW(), origine
                if type_maa == 'DENSE_FG': 
                    return data.occurrence_brouillard_dense(), origine
                
            except Exception as e:
                print('From question_declenche:', e)
                print(oaci, echeance, type_maa)
                #TODO: remonter un log sur la raison de l'erreur
        return False, None

    def question_declenche(self, oaci, echeance, type_maa, seuil=None):
        """ Fonction qui prend en charge le test déclencheur (repérage d'une occurrence ou d'un dépassement de seuil
        susceptible d'êtr pris en charge par un MAA.

        Comme prévu par les spécs, priorité est donnée aux données aéronautiques.
        
        Retourne True si un dépassement est observé (ou occurrence positive) et l'heure du TAF si la donnée provient 
        du conteneur aéro ou None sinon.

        A l'écriture du code, les types qui sont scuceptibles d'être automatisés et donc analysés ici sont :
            - les maa par seuil : vent (attendu des kt), tempé (attendu des °C), RR (attendu mm)
            - les maa occurrence suivants : TS, GR, SQ, FG, DENSE_FG, FZFG, FZRA, FZDZ

        Pour des questions pratiques, on délègue ce traitement à une autre fonction qui retourne également l'origine du 
        test déclenche => création des MAA OBS
        """
        reponse, origine = self.questionne_cdp(oaci, echeance, type_maa, seuil)
        return reponse      

    def get_context_TAF(self, oaci): 
        """ Permet d'extraire de l'archive les données issues du TAF """
        station = self.aero.getStation(oaci)
        if station is None:
            return "Pas de context TAF à fournir pour la station {}".format(oaci)

        lignes = []
        for echeance in station.ordered_echeances:
            lignes.append(station.get_echeance(echeance).get_donnees_origine())
        return "\n".join(lignes)

    def get_context_CDP(self, oaci): 
        """ Permet d'extraire de l'archive les données issues du TAF """
        station = self.cdp.getStation(oaci)
        if station is None:
            return "Pas de context CDP à fournir pour la station {}".format(oaci)

        lignes = []
        for echeance in station.ordered_echeances:
            lignes.append(station.get_echeance(echeance).get_donnees_origine())
        return "\n".join(lignes)

    def get_vent(self, oaci, echeance):
        """ Cette fonction d'interface permet de retourner les informations de vent qui ont servi pour le MAA
            Si l'info est dispo dans le cdp aéro, c'est elle qu'on prend. Sinon cdp h
            Le format de retour est du type : (ff, fx, dd) avec des vent en kt
        """
        data = self.aero.getStation(oaci)
        if data is not None:
            data = data.get_echeance(echeance)

        if data is None:
            # Le test sera fait par le cdp h/q
            data = self.cdp.getStation(oaci)
            if data is not None:
                data = data.get_echeance(echeance)
        if data is None:
            return None

        # A trouvé la station et l'échéance. On peut récupérer les infos de vent
        ff = data.get_mean_wind()
        fx = data.get_max_wind()
        dd = data.get_wind_dir()
        return (ff, fx, dd)
    
    def get_tempe(self, oaci, echeance):
        """ Cette fonction d'interface permet de retourner les informations de température qui ont servi pour le MAA
            L'info ne peut venir que de la température
            Le format de retour est du type : t avec des température en °C
        """
        data = self.cdp.getStation(oaci)
        if data is not None:
            data = data.get_echeance(echeance)
        if data is None:
            return None

        # A trouvé la station et l'échéance. On peut récupérer les infos de vent
        return data.get_param('t') 

def provide_manager (stations):
    """ Demande la récupération des donnnées et retourne un manager 
        Les apps extérieures peuvent donc profiter plus facilement du manager

        stations est un query du modèle Station.
        Le retour est une instance de ManagerData
    """

    # Chargement des données Aéro
    aeros = retrieveDatasAero([ (station.oaci, station.inseepp, station.outremer) for station in stations if not station.outremer])
    datas_aero = AeroDataStations()
    datas_aero.load_datas(aeros)

    datas = CDPDataStations()

    # Chargement des données métropole
    stations_metro = [ (station.oaci, station.inseepp) for station in stations if not station.outremer]
    cdph = retrieveDatasCDPH_metropole( stations_metro)
    cdpq = retrieveDatasCDPQ_metropole (stations_metro)
    datas.load_datas(cdph, False)
    datas.load_daily_datas(cdpq, datas, False) # Ajout des données quotidiennes pas encore implémenté

    # Chargement des données outre-mer
    stations_om = [(station.oaci, station.inseepp) for station in stations if station.outremer]
    cdph_om = retrieveDatasCDPH_om(stations_om)
    cdpq_om = retrieveDatasCDPQ_om(stations_om)
    datas.load_datas(cdph_om, True)
    datas.load_daily_datas(cdpq_om, datas, True) # Ajout des données quotidiennes pas encore implémenté
        
    # Chargement dans l'assembleur. C'est lui qui va répondre au tests. 
    assembleur = ManagerData(datas_aero, datas)

    return assembleur
