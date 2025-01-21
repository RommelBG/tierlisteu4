# data_processing.py

import requests
import logging
import urllib.parse
from utils import get_message

API_URL = 'https://skanderbeg.pm/api.php'

def obtenir_region_pays(pays_data):
    """
    Détermine la région d'un pays basé sur sa capitale
    """
    capital_id = pays_data.get('capital')
    if not capital_id:
        return "Inconnue"
    
    # Mapping des IDs de provinces vers les régions
    # Ces valeurs sont approximatives et peuvent être ajustées
    if 1 <= capital_id <= 1000:  # Europe de l'Ouest
        return "Europe"
    elif 1001 <= capital_id <= 2000:  # Europe de l'Est
        return "Europe"
    elif 2001 <= capital_id <= 3000:  # Afrique du Nord et Moyen-Orient
        return "Afrique"
    elif 3001 <= capital_id <= 4000:  # Asie
        return "Asie"
    elif 4001 <= capital_id <= 5000:  # Amériques
        return "Amériques"
    else:
        return "Inconnue"

def obtenir_dump_donnees_pays(id_sauvegarde, cle_api):
    logging.info("🎮 Initialisation du téléchargement du dump des données...")
    # Message sympa pour le téléchargement (player='???' si vous ne le connaissez pas ici)
    logging.info(get_message('telechargement').format(player='Visiteur'))

    params = {
        'key': cle_api,
        'scope': 'getSaveDataDump',
        'save': id_sauvegarde,
        'type': 'countriesData',
        'format': 'json'
    }
    response = requests.get(API_URL, params=params)
    
    # Masquer la clé API dans l'URL
    url = response.url
    parsed = urllib.parse.urlsplit(url)
    qs = urllib.parse.parse_qs(parsed.query)
    if 'key' in qs:
        qs['key'] = ['***HIDDEN***']
    new_query = urllib.parse.urlencode(qs, doseq=True)
    new_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, new_query, ''))
    
    if response.status_code != 200:
        logging.error(f"❌ Erreur HTTP {response.status_code} lors de la récupération des données.")
        logging.error(f"Contenu de la réponse : {response.text}")
        return None
    try:
        dump_donnees = response.json()
        if 'error' in dump_donnees:
            logging.error(f"❌ Erreur de l'API : {dump_donnees['error']}")
            return None
        return dump_donnees
    except ValueError:
        logging.error("❌ La réponse de l'API n'est pas au format JSON.")
        logging.error(f"Contenu de la réponse : {response.text}")
        return None

def extraire_pays_joues(dump_donnees, regions_filtrees=None):
    """
    Extrait les pays joués du dump de données avec filtrage par région
    """
    donnees_pays = dump_donnees.get('countries') or dump_donnees
    if not donnees_pays:
        logging.error("❌ Aucune donnée de pays trouvée dans le dump.")
        return None
    if isinstance(donnees_pays, dict):
        dict_pays = donnees_pays
    elif isinstance(donnees_pays, list):
        dict_pays = {p['i']: p for p in donnees_pays}
    else:
        logging.error("❌ Format inconnu pour les données de pays.")
        return None

    pays_joues = {}
    for tag, pays in dict_pays.items():
        player_name = pays.get('player', '').strip()
        if player_name or pays.get('was_player') == 'Yes':
            # Déterminer la région du pays
            region = obtenir_region_pays(pays)
            
            # Filtrer par région si des régions sont spécifiées
            if regions_filtrees and region not in regions_filtrees:
                continue
                
            pseudo_joueur = player_name if player_name else 'Joueur inconnu'
            pays_joues[tag] = {
                'data': pays,
                'pseudo_joueur': pseudo_joueur,
                'region': region
            }

    if not pays_joues:
        logging.error("❌ Aucun pays joué trouvé.")
        return None

    logging.info(get_message('analyse').format(player='Joueur'))
    logging.info(get_message('generation').format(player='Joueur'))

    return pays_joues, dict_pays

def accumuler_statistiques_pays(pays_joues, dict_pays):
    """
    Calcule les statistiques finales en tenant compte des pays et de leurs vassaux.
    """
    stats_pays = {}

    # Construire une mapping suzerain -> sujets
    overlord_to_subjects = {}
    for tag, pays in dict_pays.items():
        overlord = pays.get('overlord')
        if overlord:
            overlord_to_subjects.setdefault(overlord, []).append(tag)

    def accumuler_stats(tag, tags_visites):
        if tag in tags_visites:
            return {'developpement': 0, 'revenu': 0, 'FL': 0, 'qualite': 0, 'nb_vassaux': 0}
        tags_visites.add(tag)

        pays = dict_pays.get(tag)
        if not pays:
            return {'developpement': 0, 'revenu': 0, 'FL': 0, 'qualite': 0, 'nb_vassaux': 0}

        developpement = float(pays.get('total_development', 0))
        revenu = float(pays.get('monthly_income', 0))
        FL = float(pays.get('FL', 0))

        qualite = 0
        for valeur in pays.get('quality', {}).values():
            if valeur is not None:
                try:
                    qualite += float(valeur)
                except ValueError:
                    continue

        nb_vassaux = 0

        # Sujets du pays
        sujets = overlord_to_subjects.get(tag, [])
        nb_vassaux += len(sujets)

        for sujet_tag in sujets:
            stats_sujet = accumuler_stats(sujet_tag, tags_visites)
            developpement += stats_sujet['developpement'] * 0.5
            revenu += stats_sujet['revenu'] * 0.1
            FL += stats_sujet['FL']
            qualite += stats_sujet['qualite'] * 0.1
            nb_vassaux += stats_sujet['nb_vassaux']

        return {'developpement': developpement, 'revenu': revenu, 'FL': FL, 'qualite': qualite, 'nb_vassaux': nb_vassaux}

    for tag_joueur, joueur_info in pays_joues.items():
        pays_joueur = joueur_info['data']
        pseudo_joueur = joueur_info['pseudo_joueur']
        stats = accumuler_stats(tag_joueur, set())
        stats['nom'] = pays_joueur.get('countryName', tag_joueur)
        stats['pseudo_joueur'] = pseudo_joueur
        stats_pays[tag_joueur] = stats

    return stats_pays

def calculer_scores_et_tiers(stats_pays, poids):
    """
    Calcule les scores pondérés et attribue les tiers aux pays.
    """
    # Calculer d'abord les valeurs maximales en excluant les pays inactifs
    pays_actifs = {tag: pays for tag, pays in stats_pays.items() 
                  if pays['developpement'] > 0 or pays['revenu'] > 0 
                  or pays['FL'] > 0 or pays['qualite'] > 0}
    
    if not pays_actifs:
        return {}

    valeurs_max = {
        'developpement': max(p['developpement'] for p in pays_actifs.values()),
        'revenu': max(p['revenu'] for p in pays_actifs.values()),
        'FL': max(p['FL'] for p in pays_actifs.values()),
        'qualite': max(p['qualite'] for p in pays_actifs.values()),
    }

    # Calculer les scores et filtrer les pays avec un score significatif
    pays_avec_score = {}
    for tag, pays in pays_actifs.items():
        score = 0
        # Vérifier si le pays a des valeurs significatives
        if (pays['developpement'] > 0 or pays['revenu'] > 0 or 
            pays['FL'] > 0 or pays['qualite'] > 0):
            
            if valeurs_max['developpement'] > 0:
                score += (pays['developpement'] / valeurs_max['developpement']) * poids['developpement']
            if valeurs_max['revenu'] > 0:
                score += (pays['revenu'] / valeurs_max['revenu']) * poids['revenu']
            if valeurs_max['FL'] > 0:
                score += (pays['FL'] / valeurs_max['FL']) * poids['FL']
            if valeurs_max['qualite'] > 0:
                score += (pays['qualite'] / valeurs_max['qualite']) * poids['qualite']
            
            score = score * 100
            # Ne garder que les pays avec un score vraiment significatif
            if score > 0.1:  # Seuil minimal pour considérer un pays comme actif
                pays['score'] = score
                pays_avec_score[tag] = pays

    pays_tries = sorted(pays_avec_score.items(), key=lambda x: x[1]['score'], reverse=True)

    total_pays = len(pays_tries)
    if total_pays == 0:
        return {}

    tiers = {}
    for idx, (tag, donnees) in enumerate(pays_tries):
        percentile = idx / total_pays
        if percentile < 0.2:
            tier = 'S'
        elif percentile < 0.4:
            tier = 'A'
        elif percentile < 0.6:
            tier = 'B'
        elif percentile < 0.8:
            tier = 'C'
        else:
            tier = 'D'
        if tier not in tiers:
            tiers[tier] = []
        tiers[tier].append((tag, donnees))
    return tiers

def calculer_pertes_militaires(pays_joues, dict_pays):
    """
    Calcule les pertes militaires totales pour chaque pays.
    Ne garde que les pays ayant des pertes.
    """
    pertes_pays = {}
    
    for tag, joueur_info in pays_joues.items():
        pays = joueur_info['data']
        pseudo_joueur = joueur_info['pseudo_joueur']
        
        # Utiliser les noms exacts des variables de l'API Skanderbeg
        pertes_totales = int(pays.get('total_casualties', 0))
        pertes_batailles = int(pays.get('battleCasualties', 0))
        pertes_attrition = int(pays.get('attritionCasualties', 0))
        
        # Ne garder que les pays ayant des pertes
        if pertes_totales > 0:
            # Calculer le pourcentage d'attrition
            pourcentage_attrition = (pertes_attrition / pertes_totales * 100)
            
            pertes_pays[tag] = {
                'nom': pays.get('countryName', tag),
                'pseudo_joueur': pseudo_joueur,
                'pertes_totales': pertes_totales,
                'pertes_batailles': pertes_batailles,
                'pertes_attrition': pertes_attrition,
                'pourcentage_attrition': pourcentage_attrition
            }
    
    # Trier les pays par pertes totales
    pertes_triees = sorted(
        pertes_pays.items(),
        key=lambda x: x[1]['pertes_totales'],
        reverse=True
    )
    
    return pertes_triees
