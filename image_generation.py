# image_generation.py

from PIL import Image, ImageDraw, ImageFont
import os
import logging
from constants import TIERS, COULEURS_TIERS

def creer_image_tierlist(tiers, chemin_drapeaux):
    """
    Crée une image représentant la tierlist.
    :param tiers: dict tier -> list of (tag, stats)
    :param chemin_drapeaux: str, chemin vers le dossier des drapeaux
    :return: PIL.Image
    """
    largeur = 1200
    hauteur_par_tier = 220
    hauteur_image = hauteur_par_tier * len(TIERS)
    img = Image.new('RGB', (largeur, hauteur_image), color='white')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
        font_petit = ImageFont.truetype("arial.ttf", 14)
    except IOError:
        font = ImageFont.load_default()
        font_petit = ImageFont.load_default()
    
    taille_drapeau = 48  # Définir une taille constante pour le drapeau
    
    for idx, tier in enumerate(TIERS):
        y0 = idx * hauteur_par_tier
        draw.rectangle([0, y0, largeur, y0 + hauteur_par_tier], fill=COULEURS_TIERS[tier])
        draw.text((10, y0 + 10), f"Tier {tier}", fill='black', font=font)
        if tier in tiers:
            x = 120
            for tag, donnees in tiers[tier]:
                image_drapeau = obtenir_image_drapeau_pays(tag, chemin_drapeaux)
                if image_drapeau:
                    image_drapeau = image_drapeau.resize((taille_drapeau, taille_drapeau))
                    img.paste(image_drapeau, (x, y0 + 30))
                else:
                    # Dessiner un rectangle gris pour le drapeau manquant
                    draw.rectangle(
                        [x, y0 + 30, x + taille_drapeau, y0 + 30 + taille_drapeau],
                        fill='#CCCCCC',
                        outline='#999999'
                    )
                
                tag_et_pseudo = f"{tag} ({donnees.get('pseudo_joueur', 'N/A')})"
                texte = (
                    f"{tag_et_pseudo}\n"
                    f"FL: {donnees['FL']:.0f}\n"
                    f"Dev: {donnees['developpement']:.0f}\n"
                    f"Revenu: {donnees['revenu']:.2f}\n"
                    f"Qualité: {donnees['qualite']:.2f}\n"
                    f"Vassaux: {donnees['nb_vassaux']}\n"
                    f"Score: {donnees['score']:.2f}"
                )
                draw.multiline_text((x, y0 + 85), texte, fill='black', font=font_petit)
                x += 182
    return img

def obtenir_image_drapeau_pays(tag, chemin_drapeaux):
    extensions_possibles = ['.png', '.jpg', '.jpeg', '.tga']
    for ext in extensions_possibles:
        nom_fichier_drapeau = f"{tag.lower()}{ext}"
        path = os.path.join(chemin_drapeaux, nom_fichier_drapeau)
        if os.path.exists(path):
            try:
                return Image.open(path)
            except Exception as e:
                logging.error(f"Erreur lors de l'ouverture du drapeau pour {tag}: {e}")
                return None
    logging.warning(f"Drapeau non trouvé pour {tag}. Utilisation du drapeau par défaut.")
    chemin_drapeau_defaut = os.path.join(chemin_drapeaux, "default_flag.png")
    if os.path.exists(chemin_drapeau_defaut):
        try:
            return Image.open(chemin_drapeau_defaut)
        except Exception as e:
            logging.error(f"Erreur lors de l'ouverture du drapeau par défaut: {e}")
            return None
    else:
        logging.error("Drapeau par défaut introuvable.")
        return None
