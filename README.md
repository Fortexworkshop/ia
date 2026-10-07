# FORTEX — SENTINEL-X : l'avant-poste industriel du futur

Prototype cyber-physique complet du consortium FORTEX (Workshop EPSI Bac+4 2026). Un boîtier
ESP8266 surveille une micro-centrale AetherCorp. Le PC Serveur Local (option B) centralise les
mesures, détecte les intrusions par webcam et prédit les incidents (surchauffe, fuite de gaz),
le tout en flux chiffrés.

**Ce dépôt contient tout le projet.** Les dépôts `infra` et `dev` y sont intégrés avec leur
historique Git (`git subtree`).

| Dossier | Filière | Contenu |
|---|---|---|
| `firmware/` | DEV | Firmware C++ de l'ESP8266 : DHT22, MQ-2, PIR, OLED, MQTTS, buzzer et LEDs |
| `scripts/virtual_esp.py` | DEV | **Boîtier virtuel** (pas de capteurs physiques) : même protocole que le firmware |
| `dev/dashboard/` | DEV | Dashboard de supervision React : courbes temps réel, alertes, commandes, caméra, gestion des individus (liste blanche) |
| `backend/` | DEV | API REST + WebSocket (FastAPI), pont MQTT, stockage PostgreSQL |
| `sentinel/`, `presence/` | IA | Vision YOLOv8 (intrus), maintenance prédictive (Isolation Forest), contrôle d'accès |
| `infra/` | INFRA / CYBER | Docker Compose : Mosquitto MQTTS, PostgreSQL, backend ; certificats, comptes MQTT, ACL |
| `scripts/` | tous | Installation, lancement, simulateurs, contrôle de sécurité |
| `docs/` | tous | Documentation du dossier : IA, matrice de sécurité |

```
ESP8266 ──MQTTS 8883──► Mosquitto ──► backend (Docker) ──► PostgreSQL
 capteurs, OLED            │   ▲          │  ▲ POST /api/v1/alerts
 buzzer, LEDs ◄──commandes─┘   │          │  └──── IA : maintenance prédictive (Isolation Forest)
                               │          └──WebSocket──► dashboard React ◄── flux vidéo ── IA : vision YOLOv8 ◄── webcam USB
```

## Installation et lancement (PC Serveur Local, Windows)

Prérequis : Python 3.11, Git for Windows, Docker Desktop (démarré), Node.js.

```powershell
git clone https://github.com/Fortexworkshop/ia.git fortex
cd fortex
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -ServerIp 192.168.10.1
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

La commande `setup.ps1` est à lancer **une seule fois**. Elle installe les dépendances et les
modèles, entraîne l'IA, puis génère les secrets, la CA TLS et les comptes MQTT, ainsi que les
`.env` et la configuration du firmware (via `scripts/configure.py`). Elle lance ensuite les tests
et démarre Docker.

`start.ps1` lance Docker, puis le **boîtier virtuel**, l'IA (anomalies et vision) et le
dashboard. Ensuite :

| Adresse | Contenu |
|---|---|
| http://localhost:5173 | Dashboard de supervision |
| http://localhost:8090 | **Boîtier virtuel** : capteurs réglables, scénarios d'incident, OLED, LEDs, buzzer |
| http://localhost:8080/docs | API du backend |
| http://localhost:8081/video | Flux webcam annoté par l'IA |
| http://localhost:5000 | Contrôle d'accès (`start.ps1 -Admin`) |

**Capteurs virtuels** : l'équipe n'a pas de capteurs physiques. Le boîtier virtuel
(`scripts/virtual_esp.py`, `sentinel/virtual_box.py`) remplace l'ESP8266 et reproduit son
firmware. Il se connecte en MQTTS avec le compte `esp8266`, publie sur `sentinel/<id>/sensors`,
reçoit les commandes buzzer et LED du dashboard et déclenche l'alarme gaz locale. Les mesures ont
le bruit d'un vrai DHT22 ou MQ-2.

Scénario de démonstration : cliquer sur **Surchauffe lente** sur http://localhost:8090. L'IA
alerte vers 25 °C, bien avant le seuil critique de 40 °C. Le bouton **Fuite de gaz** déclenche,
lui, l'alarme locale.

**Avec un vrai boîtier** (si du matériel est disponible) :
1. Renseigner le Wi-Fi dans `firmware/sentinel-x/include/sentinel_config.h`, qui est généré
   automatiquement.
2. Flasher avec `.venv\Scripts\pio run -t upload`, depuis `firmware/sentinel-x`.
3. Lancer `start.ps1 -RealEsp`.

**Vérifications** :
- `python -m pytest -q` : tests automatisés ;
- `python scripts/check_security.py` : 7 contrôles de sécurité (TLS, comptes, ACL, jeton) ;
- `python scripts/bench_vision.py` : latence de la vision (< 100 ms).

**Documentation du dossier** :
- [docs/IA.md](docs/IA.md) : IA, modèles, mesures et résultats ;
- [docs/SECURITE.md](docs/SECURITE.md) : matrice de sécurité ;
- [firmware/README.md](firmware/README.md) : firmware et schéma de câblage ;
- [infra/README.md](infra/README.md) : infrastructure.

**Secrets** : aucun dans Git. `.env`, `infra/.env`, `infra/certs/`, `infra/mqtt-users.env` et
`sentinel_config.h` sont générés localement et ignorés.

**Mettre à jour depuis les dépôts d'origine**, si l'équipe y travaille encore :
`git subtree pull --prefix=infra https://github.com/Fortexworkshop/infra.git main`, et de même
pour `dev` avec `--prefix=dev`.

---

## Backend (`backend/`)

Le backend relie toutes les briques. Il tourne dans Docker (service `backend` de
`infra/docker-compose.yml`), sur le port 8080. Pour le developpement, il peut aussi tourner hors
Docker avec `python scripts/backend.py`.

```
ESP8266 ──MQTTS sentinel/<id>/sensors──► backend ──► PostgreSQL (tables du depot infra)
IA ──POST /api/v1/alerts (Bearer)────►    │    ──► WebSocket /ws ──► dashboard
dashboard ──POST /api/v1/commands──►      └──► MQTTS sentinel/<id>/commands ──► ESP8266 (buzzer, LED)
```

| Route | Role |
|---|---|
| `GET /health` | Etat : base, MQTT, age de la derniere mesure |
| `POST /api/v1/alerts` | Recoit une alerte (jeton `SENTINEL_API_TOKEN`) |
| `GET /api/v1/alerts`, `POST /api/v1/alerts/{id}/ack` | Historique des alertes, acquittement |
| `GET /api/v1/readings` | Dernieres mesures des capteurs |
| `GET /api/v1/devices` | Statut des boitiers (table `statut_boitier`) |
| `POST /api/v1/commands` | `{"actuator": "buzzer"\|"led", "state": true}` publie sur MQTT |
| `POST /api/v1/test/{heat\|gas\|intrusion}` | Alerte de test (plateforme de test du dashboard) |
| `GET /api/v1/people` | Individus de la liste blanche (données + visage) |
| `POST /api/v1/people` | Ajoute ou modifie un individu (jeton) : `{"name", "role", "notes", "photo"}` ; `photo` (base64) crée l'empreinte faciale. `previous` pour renommer |
| `DELETE /api/v1/people/{name}` | Retire un individu (jeton) : données et empreinte faciale (droit à l'effacement) |
| `GET /api/v1/presence` | Journal de présence : détections et pointages |
| `POST /api/v1/presence` | Ajoute un événement (jeton) : `{"kind": "detection"\|"entree"\|"pause"\|"reprise"\|"sortie", "person"}` |
| `GET /api/v1/vision`, `POST /api/v1/vision/start\|stop` | État et pilotage du script de vision (jeton pour les actions) |
| `WS /ws` | Temps reel, au format du dashboard : `reading`, `alert`, `command-ack` |

Documentation interactive de l'API : http://localhost:8080/docs.

- **Base de donnees** : dans Docker, le backend joint PostgreSQL par le reseau interne (aucun port
  publie). Hors Docker, il lit les identifiants dans `infra/.env` et attend la base sur
  `localhost:5433` (`FORTEX_DB_HOST`, `FORTEX_DB_PORT`). Si la base est injoignable, le backend
  continue de tourner, avec un stockage en memoire.
- **Garde-fou de dernier recours** (`SafetyAlarm`, source `garde-fou`) : ce n'est **pas** la
  maintenance predictive. L'IA (Isolation Forest, sans seuil statique) alerte *avant* l'incident.
  Le garde-fou, lui, sonne quand le seuil critique est *deja* atteint (40 °C, gaz 600, mouvement
  PIR), pour que le site reste protege meme si l'IA est arretee. Desactivable avec
  `FORTEX_SAFETY_ALARMS=0`.
- **Dashboard** : `VITE_API_URL=http://localhost:8080` dans le `.env` du dashboard. Le client
  `src/data/api.js` respecte le meme contrat que le simulateur.
- **Formats capteurs acceptes** (`sentinel/sensors.py`) : celui du firmware
  (`temperature`, `humidity`, `gas`, `pir` sur `sentinel/<id>/sensors`) et celui du simulateur
  infra (`humidite`, `niveau_gaz`, `presence` sur `fortex/capteurs/mesures`).

## Intelligence artificielle (`sentinel/`)

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
- **Journal de presence (`--pointage`)** : alimente la page « Presence » du dashboard. Une ligne
  « personne detectee » a chaque apparition (nom si le visage est reconnu), et un pointage tenu
  8 images de suite : **entree** (pouce en haut), **pause** puis **reprise** (pouce de cote,
  alterne comme dans `presence/attendance.py`) ou **sortie** (pouce en bas). `--pointage`
  active aussi la liste blanche : seules les personnes reconnues peuvent pointer.
  `--gesture-every N` (defaut 2) ne lance la detection de main qu'une image sur N : sans cela le
  geste ajoute ~40 ms et la latence depasse l'exigence des 100 ms.
- **Flux pour le dashboard** : `<img src="http://<serveur>:8081/video">`, la derniere image sur
  `/snapshot.jpg` et l'etat en JSON sur `/status`.
- **Camera exclusive** : la webcam ne s'ouvre qu'une fois a la fois. La page « Camera » du
  dashboard propose donc **Arreter / Demarrer la vision** (`POST /api/v1/vision/start|stop`) :
  arreter le script libere `/dev/video0` pour les autres applications. Sans script en cours, le
  bouton le relance avec les memes options (`--pointage`).
- Taille d'inference par defaut `--imgsz 480`, mesuree sur la webcam du PC serveur avec `scripts/bench_vision.py` : 32 ms en moyenne, 34 ms au 95e centile (640 : 124 ms au 95e centile, hors exigence).

### Plateforme web : agents et test d'image (`sentinel/admin.py`, `scripts/sentinel_admin.py`)

```powershell
python scripts/sentinel_admin.py      # puis ouvrir http://localhost:5000
```

- **Enregistrer un agent** : son nom et 1 a 10 photos du visage. L'agent est ajoute a la liste
  blanche (`data/faces.npz`), la meme que celle de `sentinel_vision.py --whitelist`.
- **Pointage par geste** : avec la webcam du navigateur (photo prise apres 3 s) ou en envoyant une
  photo. L'agent est reconnu par son visage, puis son geste enregistre l'heure :
  pouce en haut = **arrivee**, pouce sur le cote = **pause** (1er geste = depart, 2e = retour),
  pouce en bas = **sortie**.
- **Feuille de presence** : pour chaque agent et chaque jour, l'heure d'arrivee, le nombre et la
  duree des pauses, l'heure de sortie, le temps present et le statut. Export CSV possible. Les
  donnees sont dans la meme base `data/presence.db` que la borne `scripts/run.py`.
- **Tester une image** : la page affiche l'image annotee. Une personne avec un visage reconnu est
  encadree en vert (`AUTORISE`), les autres en rouge (`INTRUS`), et un visage inconnu en orange.
- **Supprimer un agent** : supprime son empreinte (droit a l'effacement).
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

### Contrats d'interface

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

Toute la configuration passe par des variables d'environnement, dans `.env` (ignore par git).
Ce fichier est genere par `scripts/configure.py`, et documente dans `.env.example` : URL de l'API,
jeton, certificat CA, broker MQTT. Si `SENTINEL_MQTT_CA_CERT` est
defini, la connexion MQTT passe en TLS. Sans `SENTINEL_API_URL`, les alertes sont seulement
affichees en console.

### Lancer les briques IA une par une (developpement)

```powershell
py -3.11 -m venv .venv ; .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q

python scripts/download_models.py                   # modeles pre-entraines (dont YOLOv8n)
python scripts/sentinel_train.py                     # entraine et evalue le modele (donnees simulees)
python scripts/mock_api.py --port 8001               # terminal 1 : fausse API qui affiche les alertes
$env:SENTINEL_API_URL="http://localhost:8001"        # terminal 2 :
python scripts/sentinel_anomaly.py --simulate        #   incident simule -> alerte ENV_ANOMALY
python scripts/fake_esp.py --incident 60             #   faux ESP8266 -> Mosquitto (avec sentinel_anomaly.py lance)
python scripts/sentinel_vision.py                    #   webcam -> alerte INTRUSION (Q pour quitter)
python scripts/sentinel_vision.py --pointage          #   + journal de presence (entree / sortie)
```

Avec le vrai ESP8266 : laisser tourner `sentinel_anomaly.py --record` une dizaine de minutes en
regime normal, puis reentrainer sur ces mesures (`sentinel_train.py --csv data/sensors.csv`). Le
modele apprend ainsi le niveau reel de la salle et des capteurs.

---

# Module `presence/` : controle d'acces du personnel (visage + geste du pouce)

Module `presence/` : borne de pointage autonome (`scripts/run.py`), aussi utilisee par la plateforme web.

Un agent (technicien, garde) se place devant la webcam a l'entree du site. L'IA **reconnait son visage**, puis **lit le geste de sa main** :

| Geste | Action enregistree |
|---|---|
| 👍 Pouce en haut | **Arrivee** (heure d'arrivee) |
| 👉 Pouce sur le cote | **Pause** : 1er geste = depart en pause, 2e geste = retour |
| 👎 Pouce en bas | **Fin** (depart ; une pause en cours est fermee automatiquement) |

## Fonctionnement

```
webcam ──► YuNet (detection visage) ──► SFace (empreinte 128D) ──► comparaison base agents ──► nom
       └─► MediaPipe Hand Landmarker (21 points de la main) ──► regles geometriques ──► geste
                                     nom + geste tenus ~8 images ──► registre SQLite
```

- **Visage** : modeles OpenCV pre-entraines (`presence/faces.py`). Chaque agent est enregistre a partir
  de quelques photos. L'empreinte moyenne est comparee par similarite cosinus (seuil 0,363).
- **Geste** (`presence/gestures.py`) : le pouce compte seulement si les 4 autres doigts sont replies et le
  pouce tendu. Sa direction (base → bout) donne l'angle : haut (±35°), bas (±35°), cote (±35°).
  Une diagonale ne declenche rien.
- **Anti faux positifs** (`presence/stabilizer.py`) : le geste doit etre tenu 8 images de suite, puis
  5 s de delai avant un nouveau geste du meme agent. Un visage inconnu ne declenche rien.
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
# 1. Enregistrer chaque agent (ESPACE pour capturer 5 photos)
python scripts/enroll.py "Alice Martin"
python scripts/enroll.py "Bob Durand" --images photos/bob/    # ou depuis un dossier de photos

# 2. Lancer la borne (Q pour quitter)
python scripts/run.py

# 3. Feuille de presence du jour (+ export CSV)
python scripts/report.py --csv data/presence.csv
```

Exemple de rapport :

```
Agent               Arrivee   Fin       Pauses  Min pause  Min presence  Statut
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
Pour le controle d'acces a un site sensible (centrale energetique), la CNIL l'admet sous
conditions strictes. Pour un deploiement reel il faudrait au minimum : information et
consentement du personnel, **alternative sans biometrie** (badge), analyse d'impact (AIPD),
traitement 100 % local (c'est le cas ici : aucune image n'est envoyee ni stockee, seulement les
empreintes), duree de conservation limitee et suppression a la demande
(`python scripts/enroll.py "Nom" --remove`).

Pour la demo du workshop, utiliser uniquement des membres de l'equipe volontaires.
