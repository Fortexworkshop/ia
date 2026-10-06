# FORTEX — Brique IA (SENTINEL-X)

Partie Intelligence Artificielle du projet FORTEX (Workshop EPSI Bac+4 2026, mission SENTINEL-X).

| Depot | Role |
|---|---|
| [Fortexworkshop/infra](https://github.com/Fortexworkshop/infra) | Docker Compose : Mosquitto (MQTT) + PostgreSQL |
| [Fortexworkshop/dev](https://github.com/Fortexworkshop/dev) | Dashboard de supervision (React) |
| **Fortexworkshop/ia** (ce depot) | Vision (intrus), maintenance predictive, plateforme eleves / pointage |

Contenu :

1. **`sentinel/`** : detection d'intrus sur la webcam (YOLOv8) et maintenance predictive sur les
   capteurs de l'ESP8266 (Isolation Forest). S'y ajoute la plateforme web pour enregistrer les
   eleves, pointer par geste du pouce et tester une image.
2. **`presence/`** : reconnaissance faciale (YuNet + SFace), lecture du geste du pouce (MediaPipe)
   et registre de presence (SQLite). Ce code est utilise par la plateforme web et par la liste
   blanche de la vision.

### Tout lancer en une commande (PC Serveur Local, Windows)

Placer les depots `infra` et `dev` a cote de ce depot, ou dans un dossier `fortex/` a cote.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1                     # une seule fois
powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -FakeEsp -Incident 60
```

`start.ps1` demarre Docker (infra), puis ouvre une fenetre par brique : maintenance predictive,
vision, dashboard et, avec `-FakeEsp`, un faux ESP8266. `-Admin` lance la plateforme eleves a la
place de la vision (une seule webcam). `-DryRun` affiche les commandes sans rien lancer.

### Branchement avec les autres depots

- **infra** : `docker compose up -d` dans le depot infra, puis `sentinel_anomaly.py` ecoute
  Mosquitto sur `localhost:1883` (voir `.env.example`).
- **dev** : dans le `.env` du dashboard, `VITE_CAMERA_URL=http://<ip-serveur>:8081/video`.
- Alertes : `POST /api/v1/alerts` des que le backend existe. Le format est decrit plus bas.
- La vision tourne **sur le PC serveur, hors Docker**, car la webcam USB n'est pas accessible
  depuis Docker Desktop sous Windows.

## SENTINEL-X : brique IA

```
                       PC Serveur Local
webcam USB ─► bridage 640x480 ─► YOLOv8n (personne) ─► [liste blanche visages] ─► 5 images de suite
                                                                                          │
ESP8266 ─MQTTS─► Mosquitto ─► fenetres glissantes 30 mesures ─► Isolation Forest ─► 10 fenetres anormales
                                                                                          │
                                         POST /api/v1/alerts (HTTPS, JSON) ◄──────────────┘
                     dashboard ◄── http://<serveur>:8081/video (MJPEG annote) + /status (JSON)
```

### Vision intelligente (`sentinel/vision.py`, `scripts/sentinel_vision.py`)

- Les images sont ramenees a 640x480 avant l'inference. YOLOv8n est filtre sur la classe COCO
  `person`. La latence de chaque image est affichee (vert < 100 ms, rouge au-dela).
- **Anti faux positifs** : une personne doit etre vue 5 images de suite. Ensuite, 10 s de delai
  avant une nouvelle alerte.
- **Liste blanche (`--whitelist`)** : une personne dont le visage est enregistre (`scripts/enroll.py`)
  est marquee « autorisee » en vert et ne declenche pas d'alerte.
- **Flux pour le dashboard** : `<img src="http://<serveur>:8081/video">`, la derniere image sur
  `/snapshot.jpg` et l'etat en JSON sur `/status`.
- Taille d'inference par defaut `--imgsz 416`. Mesure sur CPU : 640 = ~118 ms, 320 = ~44 ms par image.

### Plateforme web : eleves et test d'image (`sentinel/admin.py`, `scripts/sentinel_admin.py`)

```powershell
python scripts/sentinel_admin.py      # puis ouvrir http://localhost:5000
```

- **Enregistrer un eleve** : son nom et 1 a 10 photos du visage. L'eleve est ajoute a la liste
  blanche (`data/faces.npz`), la meme que celle de `sentinel_vision.py --whitelist`.
- **Pointage par geste** : avec la webcam du navigateur (photo prise apres 3 s) ou en envoyant une
  photo. L'eleve est reconnu par son visage, puis son geste enregistre l'heure :
  pouce en haut = **arrivee**, pouce sur le cote = **pause** (1er geste = depart, 2e = retour),
  pouce en bas = **sortie**.
- **Feuille de presence** : pour chaque eleve et chaque jour, l'heure d'arrivee, le nombre et la
  duree des pauses, l'heure de sortie, le temps present et le statut. Export CSV possible. Les
  donnees sont dans la meme base `data/presence.db` que la borne `scripts/run.py`.
- **Tester une image** : la page affiche l'image annotee. Une personne avec un visage reconnu est
  encadree en vert (`AUTORISE`), les autres en rouge (`INTRUS`), et un visage inconnu en orange.
- **Supprimer un eleve** : supprime son empreinte (droit a l'effacement).
- Le serveur n'est accessible que depuis cette machine par defaut. `--host 0.0.0.0` l'ouvre au
  reseau de la table (a eviter : donnees biometriques).

### Maintenance predictive (`sentinel/anomaly.py`, `scripts/sentinel_anomaly.py`)

- Il n'y a **aucun seuil statique**. Pour chaque fenetre glissante de 30 mesures, le script calcule
  9 indicateurs : moyenne, ecart-type et pente de la temperature, moyenne et pente de l'humidite,
  moyenne, ecart-type et pente du gaz, et correlation temperature/gaz.
- Un **Isolation Forest** (Scikit-Learn, normalisation standard, 200 arbres) apprend uniquement le
  regime normal. Le seuil est **appris** : c'est le score de la fenetre normale la plus atypique vue
  a l'entrainement. Une derive lente et correlee de la temperature et du gaz
  sort de ce profil avant le seuil critique.
- L'alerte part apres 10 fenetres anormales de suite (20 s a 1 mesure / 2 s). Sa gravite (`warning` ou `critical`) depend du
  score.
- `scripts/sentinel_train.py` affiche le taux de detection, les fausses alertes et l'**avance sur le
  seuil critique** (40 °C ou gaz 600), mesures sur des incidents simules.

### Contrats d'interface (format par defaut, a valider avec DEV et INFRA)

**Capteurs : ESP8266 vers MQTT**, topic `sentinel/<node_id>/sensors`, toutes les 2 s :
```json
{"node_id": "SENTINEL-X-01", "temperature": 23.4, "humidity": 45.1, "gas": 312, "pir": 0}
```

**Alertes : IA vers API**, `POST /api/v1/alerts`, en-tete `Authorization: Bearer <token>` :
```json
{
  "node_id": "SENTINEL-X-01",
  "source": "vision",
  "type": "INTRUSION",
  "severity": "critical",
  "message": "Presence humaine suspecte detectee (1 personne(s))",
  "timestamp": "2026-10-06T14:32:05+02:00",
  "data": {"persons": 1, "intruders": 1, "max_confidence": 0.87, "latency_ms": 54.2}
}
```
Pour `source = "anomaly"`, `type = "ENV_ANOMALY"` et `data` contient `score`, `reading` et
`features` (les indicateurs de la fenetre, utiles pour expliquer l'alerte sur le dashboard).

### Configuration

Toute la configuration passe par des variables d'environnement. Copier `.env.example` en `.env`
(ignore par git) : URL de l'API, token, certificat CA, broker MQTT. Si `SENTINEL_MQTT_CA_CERT` est
defini, la connexion MQTT passe en TLS. Sans `SENTINEL_API_URL`, les alertes sont seulement
affichees en console.

### Demarrage rapide (Windows)

```powershell
py -3.11 -m venv .venv ; .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q

python scripts/download_models.py                   # modeles pre-entraines (dont YOLOv8n)
python scripts/sentinel_train.py                     # entraine et evalue le modele (donnees simulees)
python scripts/mock_api.py                           # terminal 1 : fausse API qui affiche les alertes
$env:SENTINEL_API_URL="http://localhost:8000"        # terminal 2 :
python scripts/sentinel_anomaly.py --simulate        #   incident simule -> alerte ENV_ANOMALY
python scripts/fake_esp.py --incident 60             #   faux ESP8266 -> Mosquitto (avec sentinel_anomaly.py lance)
python scripts/sentinel_vision.py                    #   webcam -> alerte INTRUSION (Q pour quitter)
```

Avec le vrai ESP8266 : laisser tourner `sentinel_anomaly.py --record` une dizaine de minutes en
regime normal, puis reentrainer sur ces mesures (`sentinel_train.py --csv data/sensors.csv`). Le
modele apprend ainsi le niveau reel de la salle et des capteurs.

---

# Presence IA : pointage des eleves par visage et geste du pouce

Module `presence/` : borne de pointage autonome (`scripts/run.py`), aussi utilisee par la plateforme web.

L'eleve se place devant la webcam. L'IA **reconnait son visage**, puis **lit le geste de sa main** :

| Geste | Action enregistree |
|---|---|
| 👍 Pouce en haut | **Arrivee** (heure d'arrivee) |
| 👉 Pouce sur le cote | **Pause pipi** : 1er geste = depart en pause, 2e geste = retour |
| 👎 Pouce en bas | **Fin** (depart ; une pause en cours est fermee automatiquement) |

## Fonctionnement

```
webcam ──► YuNet (detection visage) ──► SFace (empreinte 128D) ──► comparaison base eleves ──► nom
       └─► MediaPipe Hand Landmarker (21 points de la main) ──► regles geometriques ──► geste
                                     nom + geste tenus ~8 images ──► registre SQLite
```

- **Visage** : modeles OpenCV pre-entraines (`presence/faces.py`). Chaque eleve est enregistre a partir
  de quelques photos. L'empreinte moyenne est comparee par similarite cosinus (seuil 0,363).
- **Geste** (`presence/gestures.py`) : le pouce compte seulement si les 4 autres doigts sont replies et le
  pouce tendu. Sa direction (base → bout) donne l'angle : haut (±35°), bas (±35°), cote (±35°).
  Une diagonale ne declenche rien.
- **Anti faux positifs** (`presence/stabilizer.py`) : le geste doit etre tenu 8 images de suite, puis
  5 s de delai avant un nouveau geste du meme eleve. Un visage inconnu ne declenche rien.
- **Regles** (`presence/attendance.py`) : pas de pause avant l'arrivee, pas de double arrivee,
  rien apres la fin. Une nouvelle journee repart de zero.

## Installation

```bash
cd presence_ia
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python scripts/download_models.py
```

## Utilisation

```bash
# 1. Enregistrer chaque eleve (ESPACE pour capturer 5 photos)
python scripts/enroll.py "Alice Martin"
python scripts/enroll.py "Bob Durand" --images photos/bob/    # ou depuis un dossier de photos

# 2. Lancer la borne (Q pour quitter)
python scripts/run.py

# 3. Feuille de presence du jour (+ export CSV)
python scripts/report.py --csv data/presence.csv
```

Exemple de rapport :

```
Eleve               Arrivee   Fin       Pauses  Min pause  Min presence  Statut
Alice Martin        08:30     17:00     1       6.0        504.0         parti
```

Donnees produites (dans `data/`, ignore par git) : `faces.npz` (empreintes), `presence.db` (evenements).

## Tests

```bash
pytest -q
```

Les tests couvrent la classification des gestes (rotations, main ouverte, pouce replie),
le stabilisateur, les regles de presence et la base d'empreintes.

## RGPD : a lire avant un usage reel

La reconnaissance faciale traite des **donnees biometriques**, categorie sensible (art. 9 RGPD).
La CNIL considere qu'elle est en principe **disproportionnee pour le controle de presence**,
surtout pour des eleves (souvent mineurs). Pour un deploiement reel il faudrait au minimum :
consentement explicite et **alternative sans biometrie** (badge, appel), analyse d'impact (AIPD),
traitement 100 % local (c'est le cas ici : aucune image n'est envoyee ni stockee, seulement les
empreintes), duree de conservation limitee et suppression a la demande
(`python scripts/enroll.py "Nom" --remove`).

Pour un projet pedagogique ou une demo, utiliser des volontaires majeurs et informes.
