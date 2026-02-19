# Plan de test — Coaching entraineur / athlete

## Pre-requis

- 2 comptes Garmin (email + mot de passe pour chacun)
- Navigateur Chrome (normal) + Chrome incognito (ou autre navigateur)
- URL : https://hillsrun.com

---

## Phase 1 — Creation des comptes HillsRun

### Etape 1 : Creer le compte COACH

1. Ouvrir Chrome **normal** → https://hillsrun.com/signup
2. S'inscrire avec email A (ex: stephaneroos@gmail.com)
3. Verifier : redirection vers `/dashboard`, message "Connect your Garmin"

### Etape 2 : Connecter le Garmin du COACH

1. Aller dans **Settings** → section "Garmin Account"
2. Entrer les identifiants Garmin du **compte 1**
3. Si MFA demande, entrer le code
4. Verifier : "Connected as **[nom]**" apparait, sync se lance
5. **Noter** : revenir sur Dashboard → les activites commencent a apparaitre (attendre ~1 min)

### Etape 3 : Creer le compte ATHLETE

1. Ouvrir Chrome **incognito** → https://hillsrun.com/signup
2. S'inscrire avec email B (ex: stephane.roos@gmail.com)
3. Aller dans **Settings** → connecter le **compte Garmin 2**
4. Verifier : "Connected as **[nom]**" + sync se lance

---

## Phase 2 — Verification de base

### Etape 4 : Verifier les activites

1. **Chrome normal** (coach) : Dashboard → des activites s'affichent
2. **Chrome incognito** (athlete) : Dashboard → des activites s'affichent
3. Les activites sont differentes entre les 2 comptes

### Etape 5 : Verifier l'etat DB (optionnel)

```bash
ssh nas "docker exec garmin-postgres psql -U garmin -d garmin_connect -c \"
SELECT user_id, garmin_user_id, better_auth_user_id, display_name, email
FROM garmin_user ORDER BY user_id\""
```

Attendu : **2 lignes**, chacune avec un `better_auth_user_id` different.

---

## Phase 3 — Coaching : lier coach et athlete

### Etape 6 : Generer un code invite (COACH)

1. **Chrome normal** (coach) → Settings → section "Coaching"
2. Cliquer "Generate Invite Code"
3. Un code de 8 caracteres apparait (ex: `A1B2C3D4`)
4. **Copier le code**

### Etape 7 : Racheter le code (ATHLETE)

1. **Chrome incognito** (athlete) → Settings → section "My Coaches"
2. Coller le code dans le champ → cliquer "Link"
3. Verifier : message de succes, le coach apparait dans la liste "My Coaches"

### Etape 8 : Verifier le lien cote coach

1. **Chrome normal** (coach) → Settings → section "Coaching"
2. L'athlete apparait dans la liste "Your Athletes"
3. **Sidebar** : un selecteur "Viewing as" apparait avec "My data" + le nom de l'athlete

---

## Phase 4 — Voir les donnees de l'athlete

### Etape 9 : Basculer sur les donnees athlete

1. **Chrome normal** (coach) → Sidebar → selecteur "Viewing as" → choisir l'athlete
2. Un bandeau apparait en haut : "Viewing [Nom]'s data"
3. Dashboard affiche les activites de **l'athlete** (pas les siennes)
4. Le bouton "Sync now" n'apparait pas (coach ne peut pas sync)

### Etape 10 : Revenir a ses propres donnees

1. Cliquer "Back to my data" dans le bandeau (ou selecteur → "My data")
2. Les activites du coach reapparaissent

---

## Phase 5 — Verification securite

### Etape 11 : L'athlete ne voit pas les donnees du coach

1. **Chrome incognito** (athlete) → Dashboard
2. Pas de selecteur "Viewing as" dans la sidebar (il n'est pas coach)
3. Seules ses propres activites apparaissent

---

## En cas de probleme

A chaque etape, si ca ne marche pas, noter :

- **Quelle etape** a echoue
- **Ce que tu vois** (message d'erreur, ecran vide, etc.)

Diagnostic cote serveur :

```bash
# Logs API
ssh nas "docker logs garmin-api --tail 30 2>&1"

# Etat garmin_user
ssh nas "docker exec garmin-postgres psql -U garmin -d garmin_connect -c \"
SELECT user_id, garmin_user_id, better_auth_user_id, display_name, email
FROM garmin_user ORDER BY user_id\""

# Etat coach_athletes
ssh nas "docker exec garmin-postgres psql -U garmin -d garmin_connect -c \"
SELECT * FROM coach_athletes\""
```
