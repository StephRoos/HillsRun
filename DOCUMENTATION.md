# Documentation du Projet HillsRun

## 📋 Vue d'ensemble

**HillsRun** est une application de suivi et d'analyse des activités de course à pied. Elle synchronise les données depuis **Garmin Connect** (montre de sport Garmin), les stocke dans une base de données **SQLite**, et les visualise via un **tableau de bord interactif Streamlit**.

### Technologie utilisée
- **Langage** : Python 3.13+
- **Gestionnaire de dépendances** : uv
- **Interface** : Streamlit (tableau de bord web)
- **Base de données** : SQLite
- **Visualisations** : Plotly

### Objectif principal
Permettre aux coureurs de synchroniser automatiquement leurs activités Garmin, visualiser des statistiques détaillées et analyser leur progression au fil du temps.

---

## 🏗️ Architecture générale

L'application est structurée en **3 modules principaux** :

```
HillsRun/
├── main.py                 # Application Streamlit (interface utilisateur)
├── garmin_client.py        # Client Garmin Connect (récupération données)
├── database.py             # Gestion SQLite (stockage/requêtes)
├── pyproject.toml          # Configuration projet uv
├── .env                    # Variables d'environnement (credentials)
└── hillsrun.db            # Base de données SQLite (créée automatiquement)
```

### Flux de données

```
Garmin Connect API
         ↓
  GarminClient (garmin_client.py)
         ↓
   SQLite Database (database.py)
         ↓
  Streamlit Dashboard (main.py)
```

---

## 📦 Dépendances

```
garminconnect>=0.2.38    # API pour récupérer les données Garmin
pandas>=2.3.3            # Manipulation et analyse de données
plotly>=6.5.2            # Graphiques interactifs
python-dotenv>=1.2.1     # Chargement variables d'environnement
streamlit>=1.54.0        # Framework dashboard web
```

---

## 🔐 Configuration initiale

Créer un fichier `.env` à la racine du projet :

```env
GARMIN_EMAIL=votre.email@gmail.com
GARMIN_PASSWORD=votre_mot_de_passe
```

⚠️ **Important** : Le fichier `.env` ne doit jamais être commité (vérifiez `.gitignore`)

---

## 📱 Module 1 : `garmin_client.py` - Client Garmin Connect

### Rôle
Interface de communication avec l'API Garmin Connect pour récupérer les activités de l'utilisateur.

### Structure de la classe

```python
class GarminClient:
    def __init__(self, email: str, password: str)
    def login() -> bool
    def resume_mfa(mfa_code: str) -> None
    def get_all_activities() -> list[dict]
    def get_activities_since(since: str) -> list[dict]
```

### Détail des fonctions

#### `__init__(email, password)`
**Rôle** : Initialiser le client Garmin avec les identifiants utilisateur.

**Paramètres** :
- `email` (str) : Email Garmin Connect
- `password` (str) : Mot de passe Garmin Connect

**Contenu** :
```python
self.email = email
self.password = password
self.client = Garmin(email, password, return_on_mfa=True)
self._client_state = None
```

- Crée une instance du client Garmin avec `return_on_mfa=True` pour gérer l'authentification multi-facteur (MFA)
- `_client_state` stocke l'état de connexion en cas de MFA

---

#### `login() -> bool`
**Rôle** : Authentifier l'utilisateur auprès de Garmin Connect.

**Retour** : `True` si MFA est requis, `False` sinon

**Logique** :
1. Essaie de se connecter avec un token stocké localement (`~/.garminconnect`)
2. Si le token est invalide ou expiré, crée un nouveau client et se connecte
3. Si la réponse est `needs_mfa`, sauvegarde l'état et retourne `True`
4. Si succès sans MFA, sauvegarde le token et retourne `False`

**Cas d'usage** :
- Première connexion → MFA généralement requis
- Connexions suivantes → Token peut être réutilisé

---

#### `resume_mfa(mfa_code: str) -> None`
**Rôle** : Compléter la connexion avec le code MFA reçu sur l'appareil Garmin.

**Paramètres** :
- `mfa_code` (str) : Code à 6 chiffres envoyé à l'appareil

**Logique** :
1. Utilise `resume_login()` avec le code MFA
2. Sauvegarde le token pour les connexions futures

---

#### `get_all_activities() -> list[dict]`
**Rôle** : Récupérer **toutes** les activités de l'utilisateur.

**Retour** : Liste de dictionnaires contenant les activités

**Logique** (pagination) :
```python
activities = []
start = 0
limit = 100
while True:
    batch = self.client.get_activities(start=start, limit=limit)
    if not batch:
        break
    activities.extend(batch)
    if len(batch) < limit:
        break
    start += limit
```

- Récupère 100 activités par page
- Continue tant qu'il y a des activités
- Retourne la liste complète

**Structure d'une activité** :
```python
{
    "activityId": 123456,
    "activityName": "Ma course",
    "activityType": {"typeKey": "running"},
    "startTimeLocal": "2024-02-15 10:30:00",
    "distance": 5000.0,        # en mètres
    "duration": 1800.0,        # en secondes
    "calories": 350,
    "averageHR": 165,
    "maxHR": 180,
    "averageSpeed": 10.0,
    "elevationGain": 120.0,
    "elevationLoss": 120.0
}
```

---

#### `get_activities_since(since: str) -> list[dict]`
**Rôle** : Récupérer les activités après une date donnée (**synchronisation incrémentale**).

**Paramètres** :
- `since` (str) : Date au format `"YYYY-MM-DD HH:MM:SS"` (ex: `"2024-02-01 00:00:00"`)

**Logique** :
1. Parse la date et ajoute 1 jour pour avoir la date de fin
2. Appelle l'API Garmin avec `get_activities_by_date()`
3. Retourne uniquement les activités après cette date

**Cas d'usage** : Synchronisation rapide (récupère seulement les nouvelles activités)

---

## 💾 Module 2 : `database.py` - Gestion SQLite

### Rôle
Gérer la persistence des données avec SQLite.

### Schéma de la table

```sql
CREATE TABLE activities (
    activity_id INTEGER PRIMARY KEY,      -- Identifiant unique Garmin
    activity_name TEXT,                   -- Nom de l'activité
    activity_type TEXT,                   -- Type (running, cycling, etc.)
    start_time TEXT,                      -- Date/heure de début
    distance REAL,                        -- Distance en mètres
    duration REAL,                        -- Durée en secondes
    calories INTEGER,                     -- Calories brûlées
    average_hr INTEGER,                   -- Fréquence cardiaque moyenne
    max_hr INTEGER,                       -- Fréquence cardiaque max
    average_speed REAL,                   -- Vitesse moyenne
    elevation_gain REAL,                  -- Dénivelé positif
    elevation_loss REAL                   -- Dénivelé négatif
)
```

### Détail des fonctions

#### `_get_connection() -> sqlite3.Connection`
**Rôle** : Créer une connexion à la base de données.

**Utilisation interne** : Tous les autres fonctions l'utilisent.

```python
return sqlite3.connect(DB_PATH)  # DB_PATH = "hillsrun.db"
```

---

#### `init_db() -> None`
**Rôle** : Initialiser la base de données au démarrage de l'application.

**Logique** :
1. Crée une connexion SQLite
2. Exécute `CREATE TABLE IF NOT EXISTS` (ne crée que si inexistante)
3. Valide la transaction et ferme la connexion

**Exécution** : Appelée une fois au démarrage dans `main.py`

---

#### `save_activities(activities: list[dict]) -> None`
**Rôle** : Sauvegarder ou mettre à jour les activités reçues de Garmin.

**Paramètres** :
- `activities` : Liste d'activités retournées par Garmin

**Logique** :
1. Itère sur chaque activité
2. Extrait le `typeKey` du dictionnaire `activityType`
3. Utilise `INSERT OR REPLACE` pour insérer ou mettre à jour si l'ID existe
4. Valide toutes les modifications

**Cas d'usage** :
- Première synchronisation : insère toutes les activités
- Synchronisations suivantes : remplace les activités existantes (si modifiées) + insère les nouvelles

---

#### `get_all_activities() -> list[dict]`
**Rôle** : Récupérer **toutes** les activités stockées, triées par date décroissante.

**Logique** :
1. Configure `row_factory` pour convertir les lignes en dictionnaires
2. Exécute : `SELECT * FROM activities ORDER BY start_time DESC`
3. Retourne la liste de dictionnaires

**Utilisé par** : `main.py` pour remplir le tableau de bord

---

#### `get_latest_activity_date() -> str | None`
**Rôle** : Obtenir la date de la dernière activité synchronisée.

**Retour** : Chaîne au format `"YYYY-MM-DD HH:MM:SS"` ou `None` si vide

**Logique** :
```sql
SELECT MAX(start_time) FROM activities
```

**Cas d'usage** : Détermine le point de départ pour la synchronisation incrémentale

---

#### `get_activity_stats() -> dict`
**Rôle** : Calculer les statistiques globales pour le tableau de bord.

**Retour** : Dictionnaire avec clés :
- `total_activities` : Nombre total d'activités
- `total_distance` : Distance totale en mètres
- `total_duration` : Durée totale en secondes
- `avg_hr` : Fréquence cardiaque moyenne

**Requête SQL** :
```sql
SELECT
    COUNT(*) as total_activities,
    COALESCE(SUM(distance), 0) as total_distance,
    COALESCE(SUM(duration), 0) as total_duration,
    COALESCE(AVG(average_hr), 0) as avg_hr
FROM activities
```

**Utilisé par** : `main.py` pour afficher les métriques principales (KPIs)

---

## 🎨 Module 3 : `main.py` - Application Streamlit

### Rôle
Interface utilisateur interactive pour synchroniser les données et visualiser les statistiques.

### Architecture

```
┌─────────────────────────────────────┐
│       Streamlit App Configuration   │
│  - Page title, icon, layout         │
│  - Initialize database              │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│   Sidebar - Synchronisation         │
│  - Email/Password fields            │
│  - Sync mode (Incr/Full)            │
│  - MFA code input                   │
│  - Sync button                      │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│      Main Content - Dashboard       │
│  - KPI metrics                      │
│  - Activities table                 │
│  - Distance chart                   │
│  - Activity type pie chart          │
│  - Monthly summary table            │
└─────────────────────────────────────┘
```

### Détail des sections

#### 1. **Initialisation**
```python
load_dotenv()              # Charge variables d'environnement
init_db()                  # Initialise la base de données
st.set_page_config(...)    # Configure la page
st.title("HillsRun")       # Titre de l'application
```

---

#### 2. **Sidebar - Synchronisation**

**Rôle** : Permettre à l'utilisateur de synchroniser ses données Garmin.

##### Composants

**Email et Password** :
```python
email = os.getenv("GARMIN_EMAIL", "")
password = os.getenv("GARMIN_PASSWORD", "")
```
- Récupère les credentials du fichier `.env`
- Affiche un warning si manquants

**Sélection du mode** :
```python
sync_mode = st.radio(
    "Mode de synchronisation",
    ["Incrémentale", "Complète"],
    index=0  # "Incrémentale" sélectionné par défaut
)
```

**Gestion du MFA** :
```python
if st.session_state.get("mfa_needed"):
    mfa_code = st.text_input("Code MFA", placeholder="123456")
    if st.button("Valider MFA"):
        garmin = st.session_state["garmin_client"]
        garmin.resume_mfa(mfa_code)
        _sync_activities(garmin)
```

- Si MFA est requis lors de la connexion, affiche un champ pour entrer le code
- Stocke le client Garmin dans `session_state` pour la réutilisation

**Bouton de synchronisation** :
```python
elif st.button("Synchroniser", disabled=not email or not password):
```

- Désactivé si email ou password manquants
- Logique :
  1. Se connecte à Garmin Connect
  2. Si MFA requis → affiche champ MFA et réexécute
  3. Sinon → récupère activités et les sauvegarde

**Affichage dernière activité** :
```python
latest_date = get_latest_activity_date()
if latest_date:
    st.caption(f"Dernière activité : {latest_date}")
```

---

#### 3. **Section principale - Dashboard**

##### Contrôle d'affichage
```python
activities = get_all_activities()
if not activities:
    st.info("Aucune activité. Lancez une synchronisation...")
    st.stop()  # Arrête l'exécution
```

- Ne montre le dashboard que s'il y a des activités

##### Métriques KPI (Key Performance Indicators)
```python
stats = get_activity_stats()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Activités", stats["total_activities"])
col2.metric("Distance totale", f"{stats['total_distance'] / 1000:.1f} km")
col3.metric("Durée totale", f"{stats['total_duration'] / 3600:.1f} h")
col4.metric("FC moyenne", f"{stats['avg_hr']:.0f} bpm")
```

- Affiche 4 métriques principales côte à côte
- Convertit les unités (mètres→km, secondes→h)

---

##### Tableau des activités

```python
df = pd.DataFrame(activities)
df_display = df.copy()

# Créer colonnes formatées
df_display["distance_km"] = df_display["distance"].apply(
    lambda x: f"{x / 1000:.2f}" if x else "—"
)
df_display["duration_min"] = df_display["duration"].apply(
    lambda x: f"{x / 60:.1f}" if x else "—"
)
df_display["allure"] = df_display.apply(
    lambda row: (
        f"{row['duration'] / 60 / (row['distance'] / 1000):.2f}"
        if row.get("distance") and row["distance"] > 0 and row.get("duration")
        else "—"
    ),
    axis=1,
)
```

**Calcul de l'allure** :
```
Allure (min/km) = Durée (minutes) / Distance (km)
                = (duration / 60) / (distance / 1000)
```

**Affichage** : Tableau interactif Streamlit avec colonnes :
- Nom, Type, Date, Distance, Durée, Allure, FC moyenne, Dénivelé+

---

##### Graphiques

###### Graphique 1 - Distance par date
```python
df_chart["distance_km"] = df_chart["distance"] / 1000
fig = px.line(
    df_chart,
    x="start_time",
    y="distance_km",
    markers=True
)
```

- Courbe de l'évolution de la distance au fil du temps
- Permet de visualiser la progression et les variations

###### Graphique 2 - Répartition par type d'activité
```python
type_counts = df["activity_type"].value_counts().reset_index()
fig = px.pie(type_counts, names="Type", values="Nombre")
```

- Camembert montrant la répartition (running, cycling, etc.)

---

##### Résumé mensuel

```python
df_monthly["mois"] = df_monthly["start_time"].dt.to_period("M").astype(str)

monthly = (
    df_monthly.groupby("mois")
    .agg(
        activités=("activity_id", "count"),
        distance_km=("distance", lambda x: x.sum() / 1000),
        durée_h=("duration", lambda x: x.sum() / 3600),
        fc_moyenne=("average_hr", "mean"),
        d_pos=("elevation_gain", "sum"),
    )
    .sort_index(ascending=False)
    .reset_index()
)
```

**Logique** :
1. Extrait l'année-mois de `start_time`
2. Groupe par mois et agrège les statistiques
3. Trie par mois décroissant (plus récent en haut)

**Colonnes affichées** :
- Mois
- Nombre d'activités
- Distance totale (km)
- Durée totale (heures)
- FC moyenne (bpm)
- Dénivelé positif (m)

---

## 🔄 Flux d'exécution complet

### Démarrage de l'application
```
1. Utilisateur exécute : uv run main.py
2. Streamlit charge main.py
3. load_dotenv() charge GARMIN_EMAIL et GARMIN_PASSWORD
4. init_db() crée la table si inexistante
5. Page s'affiche avec sidebar
```

### Synchronisation incrémentale (par défaut)
```
1. Utilisateur clique "Synchroniser"
2. GarminClient.login()
   a. Essaie connexion avec token existant
   b. Si fails → nouvelle connexion + MFA
3. Si MFA requis :
   a. Affiche input code MFA
   b. Utilisateur entre 123456
   c. GarminClient.resume_mfa()
4. get_latest_activity_date() récupère dernier timestamp
5. GarminClient.get_activities_since(latest_date)
6. save_activities() insère/met à jour dans SQLite
7. Dashboard se rafraîchit automatiquement
```

### Synchronisation complète
```
1. Mode = "Complète"
2. GarminClient.get_all_activities() (pas de filtrage date)
3. Récupère toutes les activités en paginating par 100
4. save_activities() (INSERT OR REPLACE)
```

### Affichage du dashboard
```
1. get_all_activities() récupère toutes les activités
2. Si vide → affiche message et stop
3. Convertir en DataFrame Pandas
4. Calculer stats via get_activity_stats()
5. Afficher KPIs (4 colonnes)
6. Afficher tableau formaté
7. Afficher graphiques (distance, types, mensuel)
```

---

## 🚀 Commandes d'utilisation

```bash
# Installation des dépendances
uv sync

# Lancer l'application
uv run main.py

# Accéder au dashboard
# http://localhost:8501
```

---

## 📊 Cas d'usage principaux

### 1. Première utilisation
- Créer `.env` avec credentials Garmin
- Lancer l'app
- Cliquer "Synchroniser" en mode Incrémentale
- Entrer code MFA si requis
- Toutes les activités historiques sont importées

### 2. Suivi régulier
- Chaque jour, cliquer "Synchroniser" en mode Incrémentale
- Récupère uniquement les nouvelles activités
- Plus rapide qu'une synchro complète

### 3. Ré-synchronisation complète
- Basculer en mode "Complète"
- Cliquer "Synchroniser"
- Remet à jour toutes les activités (au cas où des modifications)

---

## 🎯 Résumé des fonctionnalités

| Fonctionnalité | Module | Détail |
|---|---|---|
| Connexion Garmin | `garmin_client.py` | Login + MFA handling |
| Récupération activités | `garmin_client.py` | All activities ou depuis date X |
| Stockage données | `database.py` | SQLite avec INSERT OR REPLACE |
| Synchronisation incrémentale | `main.py` + `database.py` | Récupère depuis dernière activité |
| Dashboard interactif | `main.py` | Métriques + tableaux + graphiques |
| Visualisations | `main.py` + `plotly` | Courbes, camemberts, tableaux |
| Gestion MFA | `main.py` + `garmin_client.py` | Authentification 2FA |

---

## 🔮 Améliorations potentielles

- [ ] Exporter les données en CSV/PDF
- [ ] Notifications pour nouvelles activités
- [ ] Filtrage par date/type d'activité
- [ ] Comparaison mois/année
- [ ] Géolocalisation des activités
- [ ] Palmares personnels (PB distances)
- [ ] Support multi-utilisateurs
- [ ] Cache des données pour performance
- [ ] API REST pour intégrations tierces
- [ ] Alertes sur objectifs (distance hebdo, etc.)

---

## 📝 Notes de développement

- **Thread-safe** : Streamlit gère automatiquement la session
- **Stateless API** : Garmin API est stateless, tokens stockés localement
- **Performance** : SQLite suffisant pour des milliers d'activités
- **Temps de sync** : ~1s pour 100 activités (API Garmin)

---

**Dernière mise à jour** : Février 2026
**Version** : 0.1.0
