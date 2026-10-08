# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Contexte

Projet FORTEX / SENTINEL-X (Workshop EPSI Bac+4 2026) : un boîtier ESP8266 surveille une micro-centrale, un PC serveur local (option B) centralise les mesures, détecte les intrusions par webcam et prédit les incidents. Ce dépôt contient **tout** le projet : les dépôts `infra` et `dev` y sont intégrés par `git subtree` avec leur historique (`git subtree pull --prefix=infra|dev <url> main` pour resynchroniser). Le README est en français ; le code, les commits (Conventional Commits) et les docs aussi. La cible de déploiement est un PC Windows (scripts `.ps1`, Docker Desktop, webcam hors Docker).

Pas d'ESP8266 physique : le **boîtier virtuel** (`scripts/virtual_esp.py`, `sentinel/virtual_box.py`, interface sur :8090) le remplace avec le même protocole MQTTS. `scripts/fake_esp.py` est la variante en ligne de commande.

## Commandes

Python 3.11 (`pip install -r requirements.txt`) ; dashboard avec pnpm (`pnpm install` dans `dev/dashboard`).

```bash
python -m pytest -q                              # tous les tests (tests/, pythonpath = racine)
python -m pytest tests/test_backend.py -q        # un fichier
python -m pytest tests/test_backend.py::test_x   # un test
python scripts/check_security.py                 # 7 contrôles : TLS, comptes MQTT, ACL, jeton (stack lancée)
python scripts/bench_vision.py                   # latence vision, exigence < 100 ms

python scripts/backend.py [--memory]             # backend hors Docker, :8080 (--memory : sans PostgreSQL)
python scripts/sentinel_anomaly.py               # maintenance prédictive (écoute MQTTS)
python scripts/sentinel_vision.py [--whitelist]  # vision YOLOv8, flux MJPEG :8081
python scripts/sentinel_train.py                 # entraîne l'Isolation Forest, affiche détection / fausses alertes
python scripts/sentinel_admin.py                 # plateforme agents / pointage, :5000
cd dev/dashboard && pnpm dev | pnpm build        # dashboard, :5173

# Stack Docker (mosquitto + postgres + backend), depuis infra/
./scripts/gen-certs.sh <IP-serveur> && ./scripts/gen-mqtt-users.sh && docker compose up -d --build
```

Premier lancement complet (une seule fois) : `scripts\setup.ps1 -ServerIp 192.168.10.1`, puis `scripts\start.ps1` (options `-FakeEsp -Incident 60`, `-RealEsp`, `-Admin`, `-NoVision`, `-DryRun`). `scripts/configure.py` est idempotent : il génère secrets, CA TLS, comptes MQTT, les `.env` et `sentinel_config.h` sans jamais écraser une valeur existante. Il n'y a ni linter ni CI configurés.

## Architecture

```
ESP8266 / boîtier virtuel ──MQTTS :8883──► Mosquitto ──► backend (FastAPI :8080) ──► PostgreSQL
        ▲  sentinel/<id>/commands ◄────────────────────────┘   │ ▲ POST /api/v1/alerts (Bearer)
        │                                                        │ └── sentinel/ : anomaly.py, vision.py
                                                  WebSocket /ws ▼
                                              dev/dashboard (React) ◄── MJPEG :8081 (vision)
```

- **`backend/`** : `Service` (logique : mesures, alertes, commandes) est séparé de `create_app` (routes FastAPI) ; `Hub` diffuse en WebSocket ; `store.py` a `PostgresStore` et `MemoryStore` (repli automatique si la base est injoignable) ; `mqtt_bridge.py` fait le pont MQTTS. `messages.py` convertit tout vers **le contrat du dashboard** : `{type:'reading'|'alert'|'command-ack', …}` avec les clés courtes `temp/hum/gas/pir`. Toute évolution de format doit rester compatible avec `dev/dashboard/src/data/simulator.js` et `api.js`, qui implémentent le même contrat (`subscribe/sendCommand/inject`).
- **`backend/people.py`** : liste blanche des individus du dashboard. Donnees dans `data/people.db` (SQLite), empreinte faciale dans `data/faces.npz` — **le meme fichier que `presence/`** (vision `--whitelist`, `scripts/enroll.py`, plateforme :5000) : la vision recharge ce fichier a chaud (`sentinel/whitelist.py`, controle toutes les 2 s) : un ajout ou une suppression dans « Individus » est pris en compte sans redemarrer `sentinel_vision.py`. L'empreinte est calculee par OpenCV quand il est disponible ; le conteneur backend ne l'embarque pas, et le repli est explicite (`face_error`).
- **`backend/vision.py`** : pilote le processus de vision (bouton Arreter / Demarrer de la page « Camera »). La webcam est **exclusive** : arreter le script libere `/dev/video0` pour les autres applications, le demarrer le reprend. Le backend lance `scripts/sentinel_vision.py` avec l'interpreteur courant et ecrit sa sortie dans `data/vision.log` ; il l'arrete aussi a son propre arret, sinon la camera resterait verrouillee.
- **`backend/presence.py`** : journal de presence (SQLite `data/presence_log.db`) alimente par `sentinel_vision.py --pointage` et diffuse au dashboard par WebSocket (`type: "presence"`). `kind` : `detection` (une personne se presente), `entree` (pouce en haut), `pause` / `reprise` (pouce de cote, alterne), `sortie` (pouce en bas). Le pointage par geste vit dans le processus de vision : c'est lui qui possede la webcam, et `--pointage` implique la liste blanche (seules les personnes reconnues peuvent pointer).
- **`sentinel/`** : briques IA. `anomaly.py` = fenêtres glissantes de 30 mesures → 9 indicateurs → Isolation Forest dont le seuil est **appris** (le sujet interdit les seuils statiques) ; l'alerte part après 10 fenêtres anormales de suite. `vision.py` = YOLOv8n classe `person`, image 640x480, 5 images consécutives avant alerte, liste blanche de visages (`presence/`). Les alertes sortent par `alerts.py` vers `POST /api/v1/alerts`.
- **`SafetyAlarm` (`backend/messages.py`) n'est pas l'IA** : alarme de dernier recours à seuil dur (40 °C, gaz 600, PIR), source `garde-fou`, désactivable par `FORTEX_SAFETY_ALARMS=0`. Ne pas la présenter comme de la maintenance prédictive, et ne pas y ajouter de logique ML.
- **Deux formats de capteurs** sont acceptés (`sentinel/sensors.py`, `parse_sensor_payload`) : firmware (`temperature/humidity/gas/pir` sur `sentinel/<id>/sensors`) et simulateur infra (`humidite/niveau_gaz/presence` sur `fortex/capteurs/mesures`).
- **Sécurité MQTT** : deux comptes seulement, `esp8266` (publie les capteurs, lit les commandes) et `serveur` (l'inverse) ; anonyme refusé. Le compte serveur ne peut pas injecter de fausses mesures, c'est volontaire. Détail dans `docs/SECURITE.md` (matrice) et `docs/IA.md`.
- **Hors Docker** : la vision (webcam USB inaccessible depuis Docker Desktop/Windows), l'IA d'anomalies et le dashboard. Le backend hors Docker lit les identifiants PostgreSQL dans `infra/.env` et attend la base sur `localhost:5433` (`FORTEX_DB_HOST/PORT`) ; dans Docker, PostgreSQL n'a aucun port publié.

## Particularités

- Données biométriques : `data/faces.npz` et `data/presence.db` (visages, pointage). La plateforme `sentinel_admin.py` n'écoute que sur localhost par défaut ; ne pas l'ouvrir au réseau sans raison.
- Jamais commités (générés par `configure.py`) : `.env`, `infra/.env`, `infra/certs/`, `infra/mqtt-users.env`, `infra/mosquitto/config/passwd`, `firmware/sentinel-x/include/sentinel_config.h`.
- Le firmware (`firmware/sentinel-x`, PlatformIO) n'est pas couvert par `pytest`.
- Plusieurs tests utilisent `pytest.importorskip` : un test « passé » peut en réalité avoir été ignoré faute de dépendance (fastapi, mediapipe…). Vérifier le compte des tests ignorés.
