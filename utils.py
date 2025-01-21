# utils.py
import random
import logging
import streamlit as st

class StreamlitHandler(logging.Handler):
    def emit(self, record):
        # Ne pas afficher les messages WARNING et ERROR concernant les drapeaux
        if "Drapeau" in record.msg:
            return
        msg = self.format(record)
        st.text(msg)

def initialiser_logging():
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    logger.setLevel(logging.INFO)
    # On réintroduit le StreamlitHandler
    streamlit_handler = StreamlitHandler()
    formatter = logging.Formatter('%(msecs)dms - %(levelname)s - %(message)s')
    streamlit_handler.setFormatter(formatter)
    logger.addHandler(streamlit_handler)

    # Si vous voulez réduire les logs externes (ex: urllib3, PIL)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)


PHRASES_ETAPE_TELECHARGEMENT = [
    # Phrases informatiques ajoutées
    "Initiation du téléchargement des ressources nécessaires.",
    "Démarrage du thread de téléchargement, collecte des octets en cours.",
    "Connexion établie avec le serveur de données.",
    "Paquets de données reçus et en cours de traitement.",
    "Téléchargement terminé avec succès."
]

PHRASES_ETAPE_ANALYSE = [
    # Phrases informatiques ajoutées
    "Début de l'analyse des données collectées.",
    "Exploration des structures de données et des dépendances.",
    "Identification des tendances et des anomalies.",
    "Application des algorithmes de tri et de filtrage.",
    "Analyse complétée, résultats prêts pour la génération."
]

PHRASES_ETAPE_GENERATION = [
    # Phrases informatiques ajoutées
    "Début de la génération de la tierlist.",
    "Exécution des scripts de classement et d'agrégation.",
    "Optimisation des positions dans la tierlist en cours.",
    "Vérification des dépendances et des priorités des éléments.",
    "Tierlist finalisée et prête à être affichée."
]

def get_message(etape):
    """
    Retourne un message aléatoire correspondant à l'étape avec une variété de styles.
    etape : str - peut être 'telechargement', 'analyse', 'generation'
    """
    if etape == 'telechargement':
        return random.choice(PHRASES_ETAPE_TELECHARGEMENT)
    elif etape == 'analyse':
        return random.choice(PHRASES_ETAPE_ANALYSE)
    elif etape == 'generation':
        return random.choice(PHRASES_ETAPE_GENERATION)
    else:
        return "Étape inconnue, mais la campagne continue."

# Exemple d'utilisation
if __name__ == "__main__":
    etapes = ['telechargement', 'analyse', 'generation']
    for etape in etapes:
        print(f"{etape.capitalize()} : {get_message(etape)}")
