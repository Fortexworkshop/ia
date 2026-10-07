# SENTINEL-X — Documentation de la brique Intelligence Artificielle

*Consortium FORTEX — Workshop EPSI Bac+4, octobre 2026. Dépôt : `Fortexworkshop/ia`.*

La brique IA protège la micro-centrale AetherCorp contre deux des trois menaces du cahier des
charges : **l'intrusion physique** (vision par ordinateur sur la webcam USB) et **les risques
environnementaux** (surchauffe, fuite de gaz) par maintenance prédictive. Tout s'exécute en local
sur le PC Serveur Local (option B) : aucune image ni mesure ne quitte la table.

```
                                PC Serveur Local
webcam USB ─► bridage 640x480 ─► YOLOv8n « person » ─► liste blanche (visage) ─► 5 images de suite
                                                                                         │
ESP8266 ─MQTT─► Mosquitto ─► fenêtres de 30 mesures ─► Isolation Forest ─► 10 fenêtres anormales
                                                                                         │
                            backend FORTEX ◄── POST /api/v1/alerts (JSON + jeton Bearer) ┘
                     PostgreSQL ◄──┘  └──► WebSocket ──► dashboard de supervision
```

---

## 1. Vision intelligente : détection d'intrusion

**Script** : `scripts/sentinel_vision.py` (module `sentinel/vision.py`).

| Étape | Choix | Justification |
|---|---|---|
| Capture | Webcam USB branchée sur le PC serveur, OpenCV | Exigé par le sujet |
| Bridage | Redimensionnement systématique en **640x480** | Exigé par le sujet, coût de calcul constant |
| Modèle | **YOLOv8n** (Ultralytics), pré-entraîné sur COCO, filtré sur la classe `person` | Plus petit modèle YOLOv8, temps réel sur CPU |
| Taille d'inférence | **480 px** | Meilleur compromis mesuré (voir tableau) |
| Seuil de confiance | 0,5 | Écarte les détections douteuses |
| Anti faux positifs | Personne vue **5 images de suite**, puis **10 s** entre deux alertes | Un reflet ou une image isolée ne déclenche rien |
| Liste blanche | Visage reconnu (YuNet + SFace, similarité cosinus ≥ 0,363) dans la boîte de la personne | Un technicien autorisé n'est pas un intrus |
| Sorties | Alerte `INTRUSION` (gravité `critical`), flux vidéo annoté MJPEG `:8081/video` | Dashboard et historique |

### Performance mesurée (exigence : < 100 ms par trame)

Mesure sur la webcam du PC serveur, CPU uniquement, 40 images par taille
(`python scripts/bench_vision.py`). Latence = bridage + inférence.

| Taille d'inférence | Moyenne | 95e centile | Images/s | < 100 ms |
|---|---|---|---|---|
| 640 | 74 ms | 124 ms | 13,5 | non |
| **480 (retenue)** | **32 ms** | **34 ms** | **31,4** | **oui** |
| 416 | 26 ms | 28 ms | 38,2 | oui |
| 320 | 22 ms | 23 ms | 46,2 | oui |

La latence de chaque image est affichée en direct sur le flux, en vert sous 100 ms et en rouge
au-dessus, pour le prouver pendant la démo.

---

## 2. Maintenance prédictive : anomalies cinétiques

**Scripts** : `scripts/sentinel_train.py` (entraînement), `scripts/sentinel_anomaly.py` (temps
réel). Module : `sentinel/anomaly.py`.

### Pourquoi pas de seuil statique

Le sujet interdit `if temp > 40`. Un seuil ne voit l'incident qu'une fois qu'il est **déjà** là.
L'exemple du sujet, une hausse lente de température corrélée à une micro-déviation du gaz, reste
longtemps sous tout seuil raisonnable. On détecte donc **un comportement anormal**, pas une valeur
anormale.

### Données

Le DHT22 (température, humidité) et le MQ-2 (gaz, valeur analogique 0–1023) sont publiés par
l'ESP8266 toutes les 2 s sur `sentinel/<id>/sensors`.

### Indicateurs (9 par fenêtre glissante de 30 mesures, soit 1 minute)

| Capteur | Indicateurs |
|---|---|
| Température | moyenne, écart-type, **pente** (régression linéaire) |
| Humidité | moyenne, **pente** |
| Gaz | moyenne, écart-type, **pente** |
| Croisé | **corrélation température / gaz** |

Les pentes et la corrélation captent la dynamique (« cinétique ») : une dérive lente et simultanée
des deux capteurs ne ressemble à aucune fenêtre normale.

### Modèle

- Normalisation standard (`StandardScaler`), puis **Isolation Forest** (Scikit-Learn, 200 arbres).
- Apprentissage **non supervisé**, sur le régime normal uniquement : il n'est pas nécessaire
  d'avoir vécu un incident pour l'entraîner.
- **Seuil appris, pas fixé à la main** : une fenêtre est anormale si elle est plus atypique que la
  plus atypique des fenêtres normales vues à l'entraînement.
- **Confirmation** : l'alerte part après **10 fenêtres anormales consécutives** (20 s). La gravité
  (`warning` ou `critical`) dépend de l'écart au seuil.
- **Explicabilité** : l'alerte contient les 9 indicateurs de la fenêtre. Le dashboard peut afficher
  *pourquoi* l'IA a alerté (par exemple une pente du gaz de +0,63 par mesure et une corrélation
  température/gaz de 0,77).

### Entraînement

1. **Avant le boîtier** : 12 régimes normaux simulés de 600 mesures (`sentinel/simulate.py`), avec
   niveau de base, oscillation lente, bruit des capteurs et pics isolés. Les fenêtres ne chevauchent
   jamais deux séries, sinon une coupure créerait une fausse pente apprise comme « normale ».
2. **Avec le boîtier** : enregistrement d'environ 10 minutes en régime normal
   (`sentinel_anomaly.py --record`), puis réentraînement sur ces mesures réelles
   (`sentinel_train.py --csv data/sensors.csv`). Le modèle apprend ainsi le niveau réel de la salle.

### Résultats

Évaluation sur des scénarios simulés indépendants de l'entraînement : 50 incidents (surchauffe de
+0,04 °C par mesure avec dérive du gaz) et 50 séries normales de 30 minutes. Commande :
`python scripts/sentinel_train.py --runs 50`.

| Indicateur | Résultat |
|---|---|
| Incidents détectés | **50 / 50** |
| Séries normales avec fausse alerte | **1 / 50** |
| Avance sur le seuil critique (40 °C ou gaz 600) | **436 s en moyenne, 388 s au minimum** |

L'IA prévient donc **plus de 6 minutes avant** qu'une alarme à seuil ne sonne.

> Le backend conserve un **garde-fou de dernier recours** (`SafetyAlarm`) qui sonne quand le seuil
> critique est *déjà* atteint. Il est distinct de l'IA et sert à garder le site protégé si le
> service d'IA s'arrête.

---

## 3. Contrôle d'accès du personnel (innovation)

**Plateforme** : `scripts/sentinel_admin.py`, sur http://localhost:5000.

- **Liste blanche** : on enregistre un agent (technicien, garde) à partir de 1 à 10 photos. Seule
  l'empreinte faciale est conservée (128 nombres par agent), jamais les photos. La vision utilise
  cette liste pour distinguer un agent autorisé d'un intrus.
- **Registre des présences sur site** : l'agent est reconnu à son visage, puis un geste du pouce
  (MediaPipe Hand Landmarker, 21 points de la main) enregistre l'heure. Pouce en haut = entrée,
  pouce sur le côté = pause (aller, puis retour), pouce en bas = sortie. Export CSV possible.
- **RGPD** : ce sont des données biométriques (article 9). Le traitement est 100 % local et chaque
  agent peut être supprimé de la liste. Pour la démo, seuls des membres de l'équipe volontaires
  sont enregistrés.

---

## 4. Intégration avec les autres briques

| Flux | Protocole | Format |
|---|---|---|
| ESP8266 → IA, backend | MQTT `sentinel/<id>/sensors` | `{"temperature", "humidity", "gas", "pir"}` |
| IA → backend | `POST /api/v1/alerts`, jeton Bearer | `{node_id, source, type, severity, message, timestamp, data}` |
| Backend → dashboard | WebSocket `/ws` | `reading`, `alert`, `command-ack` |
| Vision → dashboard | HTTP MJPEG `:8081/video` | flux annoté |

Le secret (jeton de l'API) reste dans `.env`, exclu de Git.

---

## 5. Qualité et reproductibilité

- **62 tests automatisés** (`python -m pytest -q`) : classification des gestes, anti faux
  positifs, extraction des indicateurs, détection d'un incident avant le seuil critique, client
  d'alertes, backend (API, WebSocket, PostgreSQL en mémoire), plateforme web.
- Installation et lancement en une commande : `scripts/setup.ps1`, `scripts/start.ps1`.
- Toutes les mesures de ce document se reproduisent avec `bench_vision.py` et `sentinel_train.py`.

---

## 6. Limites et pistes

| Limite | Piste |
|---|---|
| Modèle prédictif entraîné sur données simulées tant que le boîtier n'est pas prêt | Réentraîner sur les mesures réelles (`--record`) |
| YOLOv8n pré-entraîné, non spécialisé (affiche ou écran montrant une personne = détection) | Fine-tuning sur images du site ; zone d'intérêt |
| Reconnaissance faciale sensible à l'éclairage et à l'angle | 3 à 5 photos variées par agent |
| Flux MQTT et vidéo encore en clair | MQTTS (port 8883) et HTTPS : code déjà prêt, certificats à fournir par CYBER |
| Vision hors Docker (accès webcam USB sous Windows) | Conteneur avec accès matériel sur Linux / Raspberry Pi |
