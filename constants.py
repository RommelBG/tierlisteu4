# constants.py
import os
from dotenv import load_dotenv

TIERS = ['S', 'A', 'B', 'C', 'D']

COULEURS_TIERS = {
    'S': '#FFD700',   # Or
    'A': '#C0C0C0',   # Argent
    'B': '#CD7F32',   # Bronze
    'C': '#87CEEB',   # Bleu ciel
    'D': '#FF6347'    # Rouge tomate
}

# Clé API par défaut (laisser vide si vous préférez la saisir dans l'interface)
CLE_API = os.getenv('CLE_API', '') 

# Chemin par défaut vers le dossier des drapeaux (modifiable via l'interface)
CHEMIN_DRAPEAUX = r'...\tierlisteu4\flags'  # Mettez le bon chemin

# Mode local (True) ou production (False)
# En local (http://localhost:8501), mettez True.
# En production (http://88.184.216.198:17001), mettez False.
MODE_LOCAL = True
