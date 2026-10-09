# Instructions Copilot — FORTEX / SENTINEL-X

Prototype cyber-physique (Workshop EPSI Bac+4 2026). Un boîtier ESP8266 surveille une
micro-centrale, un PC Serveur Local (Windows) centralise les mesures, détecte les intrusions par
webcam et prédit les incidents par apprentissage, le tout en flux chiffrés.

Le projet **complet** (firmware + dashboard + backend + IA + infra) est dans le dossier
`Fortex/`. Ce dossier est lui-même un dépôt Git (`Fortexworkshop/ia`) qui agrège les dépôts
`infra` et `dev` par `git subtree` (avec leur historique). **Toutes les commandes ci-dessous se
lancent depuis `Fortex/`**, sauf mention contraire. Sans indication contraire, `Chemin/…` =
`Fortex/Chemin/…`.

## Contexte à ne pas perdre de vue

- La cible de déploiement est un **PC Windows** : scripts `.ps1`, Docker Desktop, et la webcam
  USB tourne **hors Docker** (inaccessible depuis Docker Desktop/Windows).
- Il n'y a **pas de capteurs physiques** dans l'équipe : le « boîtier virtuel »
  (`scripts/virtual_esp.py`, `sentinel/virtual_box.py`, interface <http://localhost:8090>)
  remplace l'ESP8266 avec le même protocole MQTTS. `scripts/fake_esp.py` est la variante CLI.
- **Aucun linter ni CI n'est configuré.** Ne pas en supposer l'existence.

## Commandes

Prérequis : Python 3.11 (`pip install -r requirements.txt` depuis `Fortex/`), et pnpm pour le
dashboard.

```bash
# Tests (pytest.ini : testpaths=tests, pythonpath=racine)
python -m pytest -q                                      # suite complète
python -m pytest tests/test_backend.py -q                # un fichier
python -m pytest tests/test_backend.py::test_alert_message_matches_dashboard_contract -q  # un test

# Contrôles et mesures (stack lancée pour check_security)
python scripts/check_security.py        # 7 contrôles : TLS, comptes MQTT, ACL, jeton
python scripts/bench_vision.py          # latence vision (exigence < 100 ms/trame)

# Lancer une brique hors Docker (depuis Fortex/)
python scripts/backend.py [--memory]    # API :8080 (--memory : sans PostgreSQL)
python scripts/sentinel_anomaly.py      # maintenance prédictive (écoute MQTTS)
python scripts/sentinel_vision.py [--whitelist]   # vision YOLOv8, flux MJPEG :8081
python scripts/sentinel_train.py        # entraîne l'Isolation Forest, affiche détection / fausses alertes
python scripts/sentinel_admin.py        # contrôle d'accès / pointage :5000

# Dashboard React
cd dev/dashboard && pnpm install && pnpm dev      # :5173 (dev : jamais en démo)
cd dev/dashboard && pnpm build
cd dev/dashboard && pnpm run demo                 # build + preview avec en-têtes et CSP : ce que lance start.ps1
cd dev/dashboard && pnpm audit                    # vulnérabilités connues des dépendances

# Stack Docker (Mosquitto + PostgreSQL + backend + prometheus + grafana :3001), depuis infra/
./scripts/gen-certs.sh <IP-du-PC-serveur> && ./scripts/gen-mqtt-users.sh
docker compose up -d --build
```

Installation complète (une seule fois, Windows) : `scripts\setup.ps1 -ServerIp 192.168.10.1`,
puis `scripts\start.ps1` (options `-FakeEsp -Incident 60`, `-RealEsp`, `-Admin`, `-NoVision`,
`-DryRun`). `scripts/configure.py` est **idempotent** : il génère secrets, CA TLS, comptes MQTT,
les `.env` et `sentinel_config.h` **sans jamais écraser une valeur existante**.

## Architecture

```
ESP8266 / boîtier virtuel ──MQTTS :8883──► Mosquitto ──► backend (FastAPI :8080) ──► PostgreSQL
        ▲  sentinel/<id>/commands ◄──────────────────────────┘  │ ▲ POST /api/v1/alerts (Bearer)
        │                                                       │ └── sentinel/ : anomaly.py, vision.py
                                                WebSocket /ws ▼
                                            dev/dashboard (React) ◄── MJPEG :8081 (vision)
```

- **`backend/`** : la logique métier (`Service` : mesures, alertes, commandes) est séparée des
  routes FastAPI (`create_app`). `Hub` diffuse en WebSocket. `store.py` expose `PostgresStore`
  **et** `MemoryStore` (repli automatique si la base est injoignable). `mqtt_bridge.py` fait le
  pont MQTTS (le broker `infra` accepte deux formats de topics).
- **Contrat du dashboard** — `messages.py` convertit **tout** au format consommé par le front :
  `{type:'reading'|'alert'|'command-ack', …}` avec les clés courtes `temp/hum/gas/pir`. Toute
  évolution de ce format doit rester compatible avec `dev/dashboard/src/data/simulator.js` et
  `api.js`, qui implémentent le même contrat (`subscribe` / `sendCommand` / `inject`).
- **`backend/people.py`** : liste blanche des individus geree depuis le dashboard — donnees dans `data/people.db` (SQLite), empreinte faciale dans `data/faces.npz`, **le meme fichier que `presence/`** (vision `--whitelist`, `scripts/enroll.py`) : la vision `--whitelist` charge ce fichier **au demarrage** : un individu ajoute ensuite n'est pris en compte qu'apres redemarrage de `sentinel_vision.py`. `POST /api/v1/people` (jeton) cree/renomme, `DELETE /api/v1/people/{name}` efface donnees + empreinte. L'empreinte est calculee par OpenCV quand il est present ; le conteneur backend ne l'embarque pas (`face_error` explicite).
- **`backend/vision.py`** : pilote le script de vision (bouton Arreter / Demarrer de la page « Camera »). La webcam est **exclusive** (un seul client V4L2 a la fois) : arreter le script libere `/dev/video0`, le demarrer le reprend ; le backend l'arrete aussi a son propre arret. La sortie du script va dans `data/vision.log`.
- **`backend/presence.py`** : journal de presence (`data/presence_log.db`) pour la page « Presence » du dashboard, diffuse par WebSocket (`type: "presence"`). `kind` = `detection` (une personne se presente), `entree` (pouce en haut), `pause` / `reprise` (pouce de cote, alterne), `sortie` (pouce en bas). Les evenements viennent de `sentinel_vision.py --pointage` : le pointage par geste est dans le processus de vision parce qu'il possede l'unique webcam, et `--pointage` implique la liste blanche (`presence/gestures.py` + `presence/stabilizer.py`, libelles dans GESTURE_LABELS).
- **`sentinel/`** (IA) :
  - `anomaly.py` : fenêtres glissantes de 30 mesures → 9 indicateurs → Isolation Forest dont le
    seuil est **appris** (les seuils statiques type `if temp > 40` sont interdits par le sujet) ;
    l'alerte n'est émise qu'après 10 fenêtres anormales consécutives.
  - `vision.py` : YOLOv8n classe `person`, image 640×480, 5 images consécutives avant alerte,
    liste blanche de visages (`presence/`).
  - Les alertes sortent par `alerts.py` vers `POST /api/v1/alerts`.
- **`SafetyAlarm` (`backend/messages.py`) n'est PAS de l'IA** : c'est une alarme de dernier
  recours à seuil dur (40 °C, gaz 600, PIR), source `garde-fou`, désactivable par
  `FORTEX_SAFETY_ALARMS=0`. Ne pas la présenter comme de la maintenance prédictive et ne pas y
  ajouter de logique ML.
- **Deux formats de capteurs** sont acceptés (`sentinel/sensors.py`, `parse_sensor_payload` /
  `normalize`) : firmware (`temperature`/`humidity`/`gas`/`pir` sur `sentinel/<id>/sensors`) et
  simulateur infra (`humidite`/`niveau_gaz`/`presence` sur `fortex/capteurs/mesures`).
- **Hors Docker** : la vision, l'IA d'anomalies et le dashboard. Le backend hors Docker lit les
  identifiants PostgreSQL dans `infra/.env` et attend la base sur `localhost:5433`
  (`FORTEX_DB_HOST`/`FORTEX_DB_PORT`). Dans Docker, PostgreSQL n'expose aucun port.

## Conventions du projet

- **Langue** : README, documentation, commentaires et messages de commit sont en **français**.
  Les commits suivent **Conventional Commits** (`feat(scope): …`, `fix(...)`, `docs(...)`).
- **Dépôts imbriqués** : resynchroniser depuis les dépôts d'origine avec
  `git subtree pull --prefix=infra https://github.com/Fortexworkshop/infra.git main` (idem `dev`).
- **Secrets** : jamais commités. Générés localement par `configure.py` et ignorés : `.env`,
  `infra/.env`, `infra/certs/`, `infra/mqtt-users.env`, `infra/mosquitto/config/passwd`,
  `firmware/sentinel-x/include/sentinel_config.h`. Les `.env.example` ne contiennent aucune valeur
  réelle.
- **Sécurité MQTT** : deux comptes seulement — `esp8266` (publie les mesures, lit les commandes)
  et `serveur` (l'inverse). L'anonyme est refusé. Le compte serveur **ne peut pas** injecter de
  fausses mesures : c'est volontaire (vérifié par `check_security.py` et l'ACL Mosquitto).
- **Biométrie** : `data/faces.npz` et `data/presence.db` (visages, pointage). La plateforme
  `sentinel_admin.py` n'écoute que sur localhost par défaut ; ne pas l'ouvrir au réseau sans
  raison.
- **Tests** : plusieurs tests utilisent `pytest.importorskip` — un test « passé » peut en réalité
  avoir été **ignoré** faute de dépendance (fastapi, mediapipe…). Toujours regarder le nombre de
  tests ignorés rapporté par pytest.
- **Firmware** (`firmware/sentinel-x`, PlatformIO) : hors périmètre de `pytest`. Il compile avec
  les valeurs d'exemple de `sentinel_config.example.h` même sans `sentinel_config.h` (avertissement
  à la compilation). Comme l'ESP8266 s'appuie sur l'heure de compilation pour valider le
  certificat TLS, le flasher **après** avoir généré les certificats.
