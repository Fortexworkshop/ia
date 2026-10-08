# SENTINEL-X — Matrice de sécurité (durcissement et chiffrement)

*Consortium FORTEX. Contrôles vérifiés automatiquement par `python scripts/check_security.py`.*

## 1. Chiffrement des flux

| Flux | Avant | Après | Preuve |
|---|---|---|---|
| ESP8266 → broker | MQTT en clair, port 1883 | **MQTTS, TLS 1.2 minimum**, port 8883. Le certificat serveur est vérifié par l'ESP8266 (BearSSL, CA FORTEX embarquée) | Écran OLED « MQTT OK (TLS) » ; logs Mosquitto `negotiated TLSv1.3` |
| Backend, IA → broker | MQTT en clair | **MQTTS**, vérification du certificat par la CA FORTEX | `check_security.py` : TLSv1.3, `TLS_AES_256_GCM_SHA384` |
| IA → API | HTTP sans authentification | HTTP + **jeton Bearer** (secret dans `.env`, hors Git) | Requête sans jeton : HTTP 401 |
| Backend → PostgreSQL | — | Publié **sur localhost uniquement** (`127.0.0.1:5433`), injoignable depuis le réseau | `docker compose ps` : `127.0.0.1:5433->5432/tcp` |
| Grafana → PostgreSQL | — | Compte **`grafana_ro` en lecture seule** (SELECT uniquement) | `infra/postgres/init/02-grafana-readonly.sh` |

**PKI** : `infra/scripts/gen-certs.sh` crée une autorité racine « FORTEX Root CA » et un
certificat serveur RSA 2048 valable 2 ans. Il couvre les noms `mosquitto`, `localhost` et l'adresse
IP du PC serveur. La clé privée de la CA reste sur le PC serveur ; seul `ca.crt` est distribué.

## 2. Authentification et droits (moindre privilège)

| Compte MQTT | Peut publier | Peut lire | Usage |
|---|---|---|---|
| `esp8266` | `sentinel/+/sensors`, `sentinel/+/status`, `fortex/capteurs/mesures` | `sentinel/+/commands` | Boîtier, simulateur |
| `serveur` | `sentinel/+/commands` | `sentinel/+/sensors`, `sentinel/+/status`, `fortex/capteurs/mesures` | Backend, IA |
| anonyme | refusé | refusé | — |

Les mots de passe sont aléatoires (`gen-mqtt-users.sh`) et hachés dans le fichier `passwd`. Un
compte volé reste limité : le compte `serveur` **ne peut pas injecter de fausses mesures**, ce qui
a été vérifié.

## 3. Durcissement des conteneurs (`infra/docker-compose.yml`)

| Mesure | Services | Effet |
|---|---|---|
| `no-new-privileges` | tous | Aucune élévation de privilèges dans le conteneur |
| Utilisateur non-root (UID 10001) | backend | Une faille de l'API ne donne pas root |
| `cap_drop: ALL` | backend, simulateur | Aucune capacité Linux |
| `read_only: true` + `tmpfs /tmp` | backend, simulateur | Système de fichiers non modifiable |
| Rotation des logs (10 Mo × 3) | tous | MCO : le flux MQTT continu ne remplit pas le disque |
| Healthchecks | postgres, backend | Redémarrage et ordre de démarrage fiables |
| Limites Mosquitto (`max_connections 50`, `message_size_limit 4096`, `max_queued_messages 1000`) | broker | Atténue un déni de service pendant le pentest croisé |

## 4. Exposition réseau du PC serveur

| Port | Service | Exposé |
|---|---|---|
| 8883 | MQTTS | réseau de la table (ESP8266) |
| 8080 | API backend | réseau de la table (dashboard) |
| 5173 | dashboard | réseau de la table |
| 8081 | flux vidéo IA | réseau de la table |
| 5000 | contrôle d'accès (biométrie) | **localhost uniquement** |
| 5433 | PostgreSQL | **localhost uniquement** (`127.0.0.1`), pour le backend du PC serveur |
| 3001 | Grafana (supervision, MCO) | réseau de la table, compte admin obligatoire |
| 1883 | MQTT en clair | **fermé** |

Pare-feu Windows, à appliquer en PowerShell administrateur. Ces règles autorisent uniquement le
sous-réseau de la table :

```powershell
$table = "192.168.10.0/24"
New-NetFirewallRule -DisplayName "FORTEX MQTTS" -Direction Inbound -Protocol TCP -LocalPort 8883 -RemoteAddress $table -Action Allow
New-NetFirewallRule -DisplayName "FORTEX API"   -Direction Inbound -Protocol TCP -LocalPort 8080,5173,8081 -RemoteAddress $table -Action Allow
New-NetFirewallRule -DisplayName "FORTEX bloque MQTT clair" -Direction Inbound -Protocol TCP -LocalPort 1883 -Action Block
```

## 5. Secrets

- Aucun secret dans Git : les `.env`, `certs/`, `mqtt-users.env`, `passwd` et
  `firmware/.../sentinel_config.h` sont exclus par les `.gitignore`.
- Les fichiers `*.example` documentent chaque variable, avec des valeurs factices.

## 6. Données personnelles (biométrie)

Seules les empreintes faciales sont conservées (128 nombres par agent), jamais les photos : une
photo envoyée depuis le dashboard ou la plateforme est convertie en empreinte puis oubliée. Le
traitement est 100 % local, et la plateforme n'est accessible que depuis le PC serveur.

La liste est modifiable depuis le dashboard (page « Individus ») ou en ligne de commande
(`scripts/enroll.py`) : les deux écrivent dans le même `data/faces.npz`, que la vision
`--whitelist` relit **à son démarrage**. La suppression (`DELETE /api/v1/people/{name}`) efface
les données et l'empreinte (droit à l'effacement).

## 7. Application web : OWASP Top 10:2025 (dashboard et API)

| Catégorie | Risque identifié | Mesure | Preuve |
|---|---|---|---|
| A01 Contrôle d'accès | Données personnelles (individus, présence) et actions (acquittement, exercice) ouvertes à tout le réseau | Code opérateur exigé ; présence diffusée par WebSocket aux seuls clients authentifiés | `tests/test_backend.py` : accès anonyme = 401 ; WebSocket anonyme sans présence |
| A02 Configuration | Pas d'en-têtes de sécurité ; serveur de développement Vite pendant la démo ; CORS `*` par défaut | En-têtes `nosniff`, `X-Frame-Options`, `no-store` sur l'API ; CSP stricte (empreintes SHA-256, ni `unsafe-inline` ni `eval`) ; démo sur build de production (`pnpm run demo`) ; aucune origine CORS par défaut | `test_security_headers_and_no_wildcard_cors` ; 0 violation CSP au navigateur |
| A03 Chaîne d'approvisionnement | Vite ≤ 6.4.2 : 4 vulnérabilités dont 1 élevée (contournement `server.fs.deny` sous Windows) | Vite 6.4.4, lockfile pnpm, scripts d'installation limités à esbuild | `pnpm audit` : aucune vulnérabilité connue |
| A04 Cryptographie | Dashboard et API en HTTP sur le réseau de la table : le code opérateur circule en clair | — (voir § 8) | — |
| A05 Injection | Textes saisis (noms, consignes, messages) | React échappe tout rendu ; requêtes SQL paramétrées ; CSP sans script en ligne | revue de code |
| A06 Conception | Arrêt de la vision sans garde-fou ; photo sans taille maximale | Confirmation explicite et état « Vigilance » tant que la vision est arrêtée ; photo ≤ 8 Mo | `test_photo_size_is_bounded` |
| A07 Authentification | Code opérateur compilé dans le JavaScript (lisible par tous) | Code saisi par l'opérateur, gardé dans l'onglet (sessionStorage), jamais dans le bundle | contrôle automatique : code absent des scripts servis |
| A08 Intégrité | Messages temps réel et disposition locale acceptés sans contrôle | Validation de chaque message WebSocket ; disposition relue et bornée | message malformé ignoré sans plantage |
| A09 Journalisation | Aucune trace des actions de l'opérateur | `data/audit.log` : acquittement, commande, exercice, vision, individus, échec d'authentification WebSocket | journal lu après test |
| A10 Conditions exceptionnelles | Échecs d'action silencieux (console) ; une erreur de composant efface l'écran | Chaque échec est affiché à l'opérateur ; acquittement refusé = alarme rétablie ; un widget en erreur n'affecte pas les autres | tests navigateur |

## 8. Reste à la charge de l'équipe CYBER

- HTTPS pour l'API et le dashboard : reverse proxy TLS, avec la même CA (OWASP A04 : le code
  opérateur circule aujourd'hui en clair sur le réseau de la table).
- Flux vidéo (`:8081/video`) servi sans authentification : toute machine du réseau de la table voit
  la caméra. À protéger (jeton ou passage par l'API).
- Comptes opérateurs nominatifs : le code opérateur est partagé, le journal d'audit ne peut donc
  attribuer une action qu'à un poste (adresse IP), pas à une personne.
- IA prédictive : aucun signal de vie vers le serveur. Si `sentinel_anomaly.py` s'arrête, rien ne
  le signale (le dashboard l'indique « Non supervisé »).
- Accès SSH par clé uniquement (si le serveur est sous Linux ou WSL), et appliquer les règles de
  pare-feu ci-dessus.
- Pentest croisé du jeudi (Nmap, Wireshark, Metasploit) et rapport d'audit. `check_security.py`
  fournit la base de l'auto-audit.
