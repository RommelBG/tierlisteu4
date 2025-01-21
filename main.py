# main.py

import streamlit as st
from data_processing import (
    obtenir_dump_donnees_pays,
    extraire_pays_joues,
    accumuler_statistiques_pays,
    calculer_scores_et_tiers,
    calculer_pertes_militaires,
)
from image_generation import creer_image_tierlist
from constants import CLE_API, CHEMIN_DRAPEAUX
import os
import logging
from utils import initialiser_logging, get_message
import io
from PIL import Image
import csv
import time

def exporter_image(image_tierlist, format='PNG'):
    """
    Convertit l'image en bytes pour l'export
    """
    if isinstance(image_tierlist, Image.Image):
        # Si c'est déjà une image PIL
        img = image_tierlist
    else:
        # Si c'est un buffer d'image
        img = Image.open(io.BytesIO(image_tierlist))
    
    # Créer un buffer pour sauvegarder l'image
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf.getvalue()

def mettre_a_jour_tierlist():
    """
    Met à jour la tierlist avec les poids actuels sans retélécharger les données
    """
    if 'stats_pays' not in st.session_state:
        return None
    
    tiers = calculer_scores_et_tiers(st.session_state.stats_pays, st.session_state.poids)
    return creer_image_tierlist(tiers, CHEMIN_DRAPEAUX)

def ajuster_autres_poids(poids_modifie, nouvelle_valeur, poids_actuels, poids_verrouilles):
    """
    Ajuste les autres poids en respectant la limite de 100% et les poids verrouillés
    """
    # Calculer la somme des poids verrouillés (sauf celui qu'on modifie)
    somme_verrouilles = sum(v for k, v in poids_actuels.items() 
                           if k in poids_verrouilles and k != poids_modifie)
    
    # Vérifier si la nouvelle valeur ne dépasse pas la limite disponible
    limite_disponible = 1.0 - somme_verrouilles
    nouvelle_valeur = min(nouvelle_valeur, limite_disponible)
    
    # Calculer la somme des poids non verrouillés (sauf celui qu'on modifie)
    autres_poids = {k: v for k, v in poids_actuels.items() 
                   if k != poids_modifie and k not in poids_verrouilles}
    somme_autres = sum(autres_poids.values())
    
    nouveaux_poids = poids_actuels.copy()
    nouveaux_poids[poids_modifie] = nouvelle_valeur
    
    # S'il reste des poids non verrouillés à ajuster
    if autres_poids and somme_autres > 0:
        reste_disponible = limite_disponible - nouvelle_valeur
        # Répartir le reste proportionnellement
        facteur = reste_disponible / somme_autres
        for k, v in autres_poids.items():
            nouveaux_poids[k] = max(0, v * facteur)
    
    return nouveaux_poids

def exporter_donnees_csv(tiers, pertes_militaires):
    """
    Prépare les données combinées de la tierlist et des pertes militaires pour l'export CSV
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # En-têtes
    writer.writerow(['Type', 'Pays', 'Joueur', 'Tier', 'Score', 'Dev', 'Revenu', 'FL', 'Qualité', 'Pertes Totales', 'Pertes en Bataille', 'Pertes par Attrition', '% Attrition'])
    
    # Données de la tierlist
    pays_tiers = {}
    for tier, pays_list in tiers.items():
        for tag, donnees in pays_list:
            pays_tiers[tag] = {
                'tier': tier,
                'score': donnees['score'],
                'nom': donnees.get('nom', tag),
                'pseudo_joueur': donnees.get('pseudo_joueur', 'N/A'),
                'developpement': donnees.get('developpement', 0),
                'revenu': donnees.get('revenu', 0),
                'FL': donnees.get('FL', 0),
                'qualite': donnees.get('qualite', 0)
            }
    
    # Données des pertes
    pertes_dict = {tag: stats for tag, stats in pertes_militaires}
    
    # Combiner les données
    tous_pays = set(pays_tiers.keys()) | set(pertes_dict.keys())
    for tag in tous_pays:
        tier_info = pays_tiers.get(tag, {'tier': 'N/A', 'score': 0, 'nom': tag, 'pseudo_joueur': 'N/A',
                                        'developpement': 0, 'revenu': 0, 'FL': 0, 'qualite': 0})
        pertes_info = pertes_dict.get(tag, {'pertes_totales': 0, 'pertes_batailles': 0, 'pertes_attrition': 0, 'pourcentage_attrition': 0})
        
        writer.writerow([
            'Pays',
            tier_info['nom'],
            tier_info['pseudo_joueur'],
            tier_info['tier'],
            f"{tier_info['score']:.2f}",
            f"{tier_info['developpement']:.1f}",
            f"{tier_info['revenu']:.2f}",
            f"{tier_info['FL']:.1f}",
            f"{tier_info['qualite']:.2f}",
            pertes_info['pertes_totales'],
            pertes_info['pertes_batailles'],
            pertes_info['pertes_attrition'],
            f"{pertes_info['pourcentage_attrition']:.1f}"
        ])
    
    return output.getvalue()

def main():
    # Configuration de la page
    st.set_page_config(page_title="Générateur de Tierlist EU4", layout="wide")
    
    st.title("Générateur de Tierlist EU4")

    # Initialiser l'état de génération
    if 'genere' not in st.session_state:
        st.session_state.genere = False

    # Champ de saisie et bouton uniquement si pas encore généré
    if not st.session_state.genere:
        id_col, button_col = st.columns([3, 1])
        with id_col:
            id_sauvegarde = st.text_input("ID de Sauvegarde Skanderbeg :")
        with button_col:
            if st.button("Générer les Analyses", type="primary"):
                if not id_sauvegarde:
                    st.error("Veuillez entrer un ID de sauvegarde Skanderbeg.")
                    return
                if not CLE_API:
                    st.error("La clé API n'est pas définie. Veuillez la définir dans constants.py.")
                    return
                if not os.path.exists(CHEMIN_DRAPEAUX):
                    st.error("Le chemin des drapeaux n'existe pas. Veuillez le définir dans constants.py.")
                    return
                
                # Stocker l'ID dans session_state pour les exports
                st.session_state.id_sauvegarde = id_sauvegarde
                
                try:
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    # Animation initiale
                    status_text.text("🔍 Initialisation de l'analyse...")
                    for i in range(1, 4):
                        progress_bar.progress(i * 5)
                        time.sleep(0.2)

                    # Étape 1: Récupération des données
                    status_text.text("🔄 Récupération des données Skanderbeg...")
                    progress_bar.progress(20)
                    
                    dump_donnees = obtenir_dump_donnees_pays(id_sauvegarde, CLE_API)
                    if not dump_donnees:
                        st.error("Impossible de récupérer les données des pays.")
                        return
                    
                    # Animation intermédiaire
                    status_text.text("📊 Analyse des données en cours...")
                    progress_bar.progress(40)
                    time.sleep(0.3)
                    
                    result = extraire_pays_joues(dump_donnees)
                    if not result:
                        st.error("Impossible d'extraire les pays joués.")
                        return
                        
                    pays_joues, dict_pays = result
                    status_text.text("🎯 Calcul des statistiques...")
                    progress_bar.progress(60)
                    time.sleep(0.3)
                    
                    # Calcul des statistiques pour la tierlist
                    stats_pays = accumuler_statistiques_pays(pays_joues, dict_pays)
                    st.session_state.stats_pays = stats_pays
                    
                    # Calcul des pertes militaires
                    status_text.text("⚔️ Analyse des pertes militaires...")
                    pertes_triees = calculer_pertes_militaires(pays_joues, dict_pays)
                    st.session_state.pertes_militaires = pertes_triees
                    
                    progress_bar.progress(80)
                    status_text.text("🎨 Génération de la tierlist...")
                    time.sleep(0.3)

                    # Génération de la tierlist
                    tiers = calculer_scores_et_tiers(stats_pays, st.session_state.poids)
                    image_tierlist = creer_image_tierlist(tiers, CHEMIN_DRAPEAUX)
                    st.session_state.image_courante = image_tierlist
                    
                    progress_bar.progress(100)
                    status_text.text("✨ Analyses générées avec succès !")

                    # Afficher un message de succès global
                    st.success("✨ Toutes les analyses ont été générées avec succès !")
                    
                    # Marquer comme généré
                    st.session_state.genere = True
                    st.rerun()

                except Exception as e:
                    logging.error(f"Une erreur est survenue : {e}")
                    st.error(f"Une erreur est survenue : {e}")
    
    # Sidebar pour les options
    with st.sidebar:
        st.title("Options")
        
        # Personnalisation des poids
        st.header("Personnalisation des poids")
        with st.expander("Modifier les poids", expanded=True):
            # Initialisation des poids et des verrouillages
            if 'poids' not in st.session_state:
                st.session_state.poids = {
                    'developpement': 0.3,
                    'revenu': 0.3,
                    'FL': 0.2,
                    'qualite': 0.2
                }
            if 'poids_verrouilles' not in st.session_state:
                st.session_state.poids_verrouilles = set()
            
            # Fonction pour gérer le changement d'un slider
            def on_slider_change(poids_modifie):
                if poids_modifie not in st.session_state.poids_verrouilles:
                    nouvelle_valeur = st.session_state[f'{poids_modifie}_slider'] / 100
                    st.session_state.poids = ajuster_autres_poids(
                        poids_modifie, 
                        nouvelle_valeur, 
                        st.session_state.poids,
                        st.session_state.poids_verrouilles
                    )
                    if 'stats_pays' in st.session_state:
                        st.session_state.image_courante = mettre_a_jour_tierlist()
            
            # Sliders et boutons de verrouillage
            st.write("Ajustez les valeurs (0-100) et verrouillez les poids si nécessaire :")
            
            # Calculer la limite disponible pour chaque slider
            somme_verrouilles = sum(st.session_state.poids[k] for k in st.session_state.poids_verrouilles)
            
            for nom_poids, label in [
                ('developpement', 'Développement'),
                ('revenu', 'Revenu'),
                ('FL', 'Force Limite'),
                ('qualite', 'Qualité')
            ]:
                col1, col2 = st.columns([4, 1])
                with col1:
                    # Calculer la limite max pour ce slider
                    if nom_poids in st.session_state.poids_verrouilles:
                        max_value = int(st.session_state.poids[nom_poids] * 100)
                    else:
                        # Calculer l'espace disponible en excluant les poids verrouillés
                        espace_disponible = 1.0 - sum(st.session_state.poids[k] for k in st.session_state.poids_verrouilles 
                                                    if k != nom_poids)
                        max_value = int(min(1.0, espace_disponible) * 100)
                    
                    # S'assurer que max_value est au moins 1 et ne dépasse pas 100
                    max_value = max(1, min(100, max_value))
                    # S'assurer que la valeur actuelle ne dépasse pas max_value
                    current_value = min(int(st.session_state.poids[nom_poids] * 100), max_value)
                    
                    st.slider(
                        label, 
                        0, 
                        max_value,
                        current_value,
                        1,
                        key=f'{nom_poids}_slider',
                        on_change=lambda n=nom_poids: on_slider_change(n),
                        help=f"Importance de {label.lower()} (max: {max_value}%)",
                        disabled=nom_poids in st.session_state.poids_verrouilles
                    )
                with col2:
                    if st.button(
                        "🔒" if nom_poids in st.session_state.poids_verrouilles else "🔓",
                        key=f'lock_{nom_poids}'
                    ):
                        if nom_poids in st.session_state.poids_verrouilles:
                            st.session_state.poids_verrouilles.remove(nom_poids)
                        else:
                            # Vérifier s'il reste assez d'espace pour verrouiller
                            poids_actuel = st.session_state.poids[nom_poids]
                            if (somme_verrouilles + poids_actuel) <= 1:
                                st.session_state.poids_verrouilles.add(nom_poids)
                            else:
                                st.error(f"Impossible de verrouiller {label} : la somme des poids dépasserait 100%")
                        st.rerun()
            
            # Bouton pour réinitialiser les poids
            if st.button("Réinitialiser les poids", key='reset_button'):
                st.session_state.poids = {
                    'developpement': 0.3,
                    'revenu': 0.3,
                    'FL': 0.2,
                    'qualite': 0.2
                }
                st.session_state.poids_verrouilles = set()  # Déverrouiller tous les poids
                # Réinitialiser les valeurs des sliders
                st.session_state.developpement_slider = 30
                st.session_state.revenu_slider = 30
                st.session_state.FL_slider = 20
                st.session_state.qualite_slider = 20
                if 'stats_pays' in st.session_state:
                    st.session_state.image_courante = mettre_a_jour_tierlist()
                st.rerun()
        
        # Options d'export
        if 'image_courante' in st.session_state and 'pertes_militaires' in st.session_state:
            st.header("Télécharger")
            
            # Export PNG
            st.download_button(
                "Télécharger Tierlist (PNG)",
                data=exporter_image(st.session_state.image_courante, 'PNG'),
                file_name=f"tierlist_{st.session_state.id_sauvegarde}.png",
                mime="image/png"
            )
            
            # Export CSV combiné
            tiers = calculer_scores_et_tiers(st.session_state.stats_pays, st.session_state.poids)
            csv_data = exporter_donnees_csv(tiers, st.session_state.pertes_militaires)
            st.download_button(
                "Télécharger Données (CSV)",
                data=csv_data,
                file_name=f"donnees_{st.session_state.id_sauvegarde}.csv",
                mime="text/csv"
            )

    initialiser_logging()

    # Onglets principaux
    tab1, tab2 = st.tabs(["Tierlist", "Pertes Militaires"])

    with tab1:
        if 'image_courante' in st.session_state:
            # Conteneur centré pour la tierlist
            col1, col2, col3 = st.columns([1, 3, 1])
            with col2:
                st.image(st.session_state.image_courante, caption='Tierlist EU4', width=800)

    with tab2:
        if 'pertes_militaires' in st.session_state:
            # Créer un DataFrame pour un affichage plus propre
            data = []
            for tag, stats in st.session_state.pertes_militaires:
                data.append({
                    "Pays": stats['nom'],
                    "Joueur": stats['pseudo_joueur'],
                    "Pertes Totales": f"{stats['pertes_totales']:,}",
                    "Pertes en Bataille": f"{stats['pertes_batailles']:,}",
                    "Pertes par Attrition": f"{stats['pertes_attrition']:,}",
                    "% Attrition": f"{stats['pourcentage_attrition']:.1f}%"
                })
            
            # Utiliser st.dataframe pour un affichage interactif
            st.dataframe(
                data,
                column_config={
                    "Pays": st.column_config.TextColumn("Pays", width="medium"),
                    "Joueur": st.column_config.TextColumn("Joueur", width="medium"),
                    "Pertes Totales": st.column_config.TextColumn("Pertes Totales", width="medium"),
                    "Pertes en Bataille": st.column_config.TextColumn("Pertes en Bataille", width="medium"),
                    "Pertes par Attrition": st.column_config.TextColumn("Pertes par Attrition", width="medium"),
                    "% Attrition": st.column_config.TextColumn("% Attrition", width="small"),
                },
                hide_index=True,
                use_container_width=True
            )

if __name__ == "__main__":
    main()
