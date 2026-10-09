# Décisions techniques — FORTEX / SENTINEL-X

Journal des décisions structurantes, consignées **au moment où elles ont été prises** et non
reconstituées après coup. Chaque entrée suit le même format, en trois lignes :

- **Quoi** — la décision, en une phrase.
- **Pourquoi** — la contrainte ou le fait qui l'impose.
- **Écarté** — les options examinées et abandonnées, pour que la question ne soit pas rouverte.

Les décisions de rendu et de dépôt sont en fin de document.

---

## 2026-10-07 — Cadrage et socle technique

### Option B : le PC serveur local est le portable d'un apprenant

- **Quoi** : le rôle de PC serveur local est tenu par le portable d'un apprenant, qui sert aussi de
  point d'accès Wi-Fi de la table. La webcam USB y est branchée en direct.
- **Pourquoi** : le sujet autorise deux options matérielles ; l'option B est la seule qui donne au
  serveur la puissance de calcul nécessaire à l'IA de vision, sans acheter de machine dédiée.
- **Écarté** : l'option A (serveur dédié) — aucune machine disponible ; un Raspberry Pi comme
  serveur — insuffisant pour YOLOv8 en temps réel, et une surface d'attaque Linux de plus.

### Le boîtier est simulé, avec le protocole du firmware

- **Quoi** : aucun matériel n'a été distribué ; le boîtier est remplacé par `scripts/virtual_esp.py`
  et `sentinel/virtual_box.py`, qui parlent **exactement** le même MQTTS que le firmware — mêmes
  topics, même compte, mêmes commandes, même alarme locale.
- **Pourquoi** : le workshop ne fournit pas d'ESP8266 ni de capteurs. Simuler au niveau du
  protocole plutôt qu'au niveau de l'interface permet de brancher le vrai boîtier sans rien changer
  côté serveur.
- **Écarté** : un simple générateur de données injecté dans l'API — il n'aurait exercé ni le broker,
  ni l'ACL, ni les commandes descendantes.

### Un seul dépôt, agrégé par `git subtree`

- **Quoi** : `infra` et `dev` sont intégrés dans le dépôt `ia` par `git subtree`, avec leur
  historique.
- **Pourquoi** : trois dépôts séparés obligeaient à synchroniser trois clones pour une seule démo.
  `subtree` conserve l'historique d'origine et permet de republier chaque sous-dépôt à l'identique.
- **Écarté** : un monorepo sans historique — perte de la traçabilité ; des sous-modules — obligent
  chaque poste à cloner trois fois, et cassent l'installation en une commande.

### MQTT plutôt que HTTP pour les capteurs

- **Quoi** : le boîtier publie en MQTT sur Mosquitto ; l'API REST ne reçoit que les alertes de l'IA.
- **Pourquoi** : MQTT est fait pour les objets contraints — en-têtes minuscules, publication sans
  connaître l'adresse du serveur, niveaux de QoS, et surtout un **testament** (LWT) qui donne l'état
  en ligne / hors ligne sans code supplémentaire.
- **Écarté** : HTTP *polling* — plus lourd, pas de *push*, pas de testament ; CoAP — UDP et
  outillage moins mûr ; AMQP ou Kafka — hors d'échelle pour une table.

### Deux comptes MQTT, et le compte serveur ne peut pas publier de mesures

- **Quoi** : deux comptes seulement, `esp8266` (publie les capteurs, lit les commandes) et
  `serveur` (l'inverse). L'anonyme est refusé, et l'ACL interdit au compte serveur de publier sur
  le topic des mesures.
- **Pourquoi** : l'injection de fausses mesures est le scénario d'attaque le plus évident d'une
  chaîne de surveillance. Le rendre impossible par construction vaut mieux que de le détecter.
- **Écarté** : un compte unique — donne à l'IA le pouvoir de fabriquer les données qu'elle analyse.
  Vérifié par `scripts/check_security.py`.

### FastAPI

- **Quoi** : l'API REST et le WebSocket sont écrits en FastAPI.
- **Pourquoi** : asynchrone — indispensable pour servir un WebSocket *et* un pont MQTT dans le même
  processus ; validation automatique par Pydantic ; WebSocket natif ; et **même langage que l'IA**,
  donc un seul environnement Python.
- **Écarté** : Flask — synchrone et sans validation intégrée ; Django — trop lourd pour une API ;
  Node — aurait ajouté un second langage à l'équipe.

### PostgreSQL, avec repli mémoire

- **Quoi** : PostgreSQL pour l'historique, et `MemoryStore` en repli automatique si la base est
  injoignable.
- **Pourquoi** : une seule base, robuste, et Grafana la lit en SQL en lecture seule. Le repli
  mémoire garantit qu'une base absente ne fait pas échouer une démonstration.
- **Écarté** : SQLite — pas d'accès concurrent entre le conteneur et Grafana ; InfluxDB — meilleur
  en séries temporelles, mais une base de plus à exploiter pour une mesure toutes les 2 s ;
  MongoDB — inutile sans schéma flexible à exploiter.

### Docker Compose

- **Quoi** : Mosquitto, PostgreSQL, backend, Prometheus et Grafana sont décrits dans un
  `docker-compose.yml` durci.
- **Pourquoi** : installation reproductible en deux commandes sur une seule machine, et durcissement
  homogène (non-root, lecture seule, privilèges retirés) écrit une fois pour tous les services.
- **Écarté** : Kubernetes — hors d'échelle pour un PC de table ; une installation manuelle — non
  reproductible d'un poste à l'autre.

---

## 2026-10-08 — IA, sécurité, interface

### YOLOv8n, avec l'inférence ramenée à 480 px

- **Quoi** : détection de personnes par YOLOv8n, capture en 640 × 480, inférence à 480 px.
- **Pourquoi** : la variante *nano* tient le temps réel **sur CPU, sans GPU** : 32 ms en moyenne et
  34 ms au 95ᵉ centile, pour une exigence de 100 ms. À 640 px d'inférence, le 95ᵉ centile tombe à
  124 ms — hors exigence.
- **Écarté** : Faster R-CNN — trop lent ; SSD — moins précis ; RT-DETR — trop lourd sur CPU. Un
  modèle plus gros n'apporterait rien : une seule classe est utile, `person`.

### Liste blanche par YuNet + SFace (OpenCV)

- **Quoi** : la reconnaissance faciale repose sur YuNet (détection) et SFace (empreinte 128D),
  fournis avec OpenCV.
- **Pourquoi** : livrés avec une dépendance déjà présente, aucune compilation native, légers sur
  CPU. La liste blanche est petite : un modèle de reconnaissance ouvert serait surdimensionné.
- **Écarté** : dlib — compilation lourde et lent sur CPU ; InsightFace ou DeepFace — dépendances
  supplémentaires pour un gain non démontré à cette échelle.

### L'alarme intrusion part après 20 s sans reconnaissance

- **Quoi** : une personne détectée mais non reconnue pendant 20 secondes consécutives déclenche
  l'alerte, le buzzer et la LED. Auparavant, la règle portait sur 5 images consécutives.
- **Pourquoi** : 5 images représentent moins d'une seconde — un passage devant la caméra suffisait à
  sonner. 20 s est le temps de traverser le site : assez pour ne pas alerter sur un passage, trop
  court pour laisser quelqu'un s'installer (`IntruderTimer`).
- **Écarté** : un délai en secondes paramétrable par l'opérateur — une valeur qu'on peut allonger
  pendant une intrusion est un défaut, pas une fonctionnalité.

### Isolation Forest à seuil appris

- **Quoi** : la maintenance prédictive découpe le flux en fenêtres glissantes de 30 mesures, en tire
  9 indicateurs, et laisse un Isolation Forest décider — le seuil est **appris** sur les données.
- **Pourquoi** : le sujet interdit explicitement les conditions statiques du type `if temp > 40`.
  Nos incidents ne sont pas étiquetés, donc il faut du non supervisé ; et le modèle doit rester
  **explicable** devant un jury.
- **Écarté** : un autoencodeur ou un LSTM — beaucoup de données, un GPU, et une boîte noire ; One
  Class SVM — passe mal à l'échelle ; les seuils fixes — interdits par le sujet.

### 30 mesures, 9 indicateurs, 10 fenêtres consécutives

- **Quoi** : une fenêtre fait 30 mesures (une minute) ; 9 indicateurs — niveau, variabilité, pente et
  corrélation température / gaz ; l'alerte n'est émise qu'après **10 fenêtres anormales de suite**.
- **Pourquoi** : une dérive lente et simultanée de deux capteurs sort du profil normal bien avant
  d'atteindre une valeur critique. Les 10 fenêtres évitent de sonner sur une mesure isolée.
- **Écarté** : un seuil de décision choisi à la main — il faut que le nombre de fausses alertes soit
  mesuré (1 sur 50 séries normales), pas négocié.

### Le garde-fou à seuil dur reste, mais séparé de l'IA

- **Quoi** : le backend conserve `SafetyAlarm` — 40 °C, gaz 600, PIR — de source `garde-fou` et
  désactivable par `FORTEX_SAFETY_ALARMS=0`.
- **Pourquoi** : si le service d'IA s'arrête, le site reste protégé. Mais c'est une alarme de dernier
  recours, pas une prédiction : la présenter comme de la maintenance prédictive serait faux.
- **Écarté** : supprimer le garde-fou pour éviter la confusion avec l'IA — laisserait un site sans
  aucune protection en cas de panne du service d'anomalies.

### Deux jetons distincts : IA et opérateur

- **Quoi** : le jeton `API_TOKEN` (machines) peut émettre alertes et présence ; le jeton
  `DASHBOARD_TOKEN` (opérateur) peut commander, acquitter et gérer les individus, **mais pas**
  émettre d'alerte.
- **Pourquoi** : le code opérateur est saisi dans un navigateur. S'il servait aussi à injecter des
  alertes, n'importe qui pourrait fabriquer une fausse intrusion.
- **Écarté** : un jeton unique — plus simple, mais il donne au poste le plus exposé le pouvoir de
  fabriquer les événements que le poste doit vérifier.

### La charte graphique est la source unique des couleurs

- **Quoi** : toutes les couleurs et tailles vivent dans `dev/dashboard/src/tokens.css`. Aucune valeur
  en dur dans un composant, ni dans les documents générés.
- **Pourquoi** : l'interface suit les principes d'une IHM de conduite (ISA-101) — l'état normal est
  neutre, **la couleur ne signale qu'un écart** (rouge critique, ambre avertissement, violet liaison
  perdue), et le bleu acier est réservé à l'interaction.
- **Écarté** : une palette par écran — les documents auraient divergé de l'application, et le rouge
  aurait fini par décorer ce qui ne va pas mal.

### React + Vite, sans bibliothèque d'interface ni routeur

- **Quoi** : le dashboard est en React 18 avec Vite, sans bibliothèque de composants ni de routage.
- **Pourquoi** : la charte impose des composants maîtrisés (contrastes calculés, cibles de 44 px,
  états d'alarme) qu'une bibliothèque générique aurait imposé de surcharger. Seule la vue d'ensemble
  est dans le paquet principal, les autres pages sont chargées à la demande (Core Web Vitals).
- **Écarté** : Material UI ou équivalent — surcharge de styles à combattre ; un routeur — inutile
  pour cinq pages sans URL profonde.

### Une seule connexion temps réel pour tout le dashboard

- **Quoi** : `src/state/live.jsx` ouvre l'unique WebSocket et diffuse l'état ; aucune page n'ouvre la
  sienne.
- **Pourquoi** : deux écrans branchés sur deux connexions peuvent afficher deux vérités différentes
  au même instant. Pour une salle de conduite, c'est un défaut, pas une optimisation.
- **Écarté** : une connexion par page — plus simple à écrire, mais rend l'état incohérent entre les
  vues, et multiplie les reconnexions.

### Grafana et Prometheus en lecture seule, pour le MCO

- **Quoi** : `GET /metrics` expose les métriques au format Prometheus ; Grafana les affiche et lit
  PostgreSQL avec un compte restreint.
- **Pourquoi** : le dashboard sert à **agir**, Grafana à **observer et se souvenir**. Et un serveur
  qui surveille doit être surveillé : si son disque se remplit, la surveillance s'arrête sans que
  personne ne le sache.
- **Écarté** : tout mettre dans le dashboard — mélange deux métiers et deux rythmes ; une pile ELK —
  trois services à maintenir pour des journaux dont personne ne se sert pendant la démo.

---

## 2026-10-09 — Rendu et dépôt

### Le dossier et le poster sont générés depuis le dépôt

- **Quoi** : `docs/dossier/build.py` produit le dossier A4 et le poster A3 à partir de
  `docs/SECURITE.md`, `docs/IA.md` et de schémas dessinés en SVG ; `render.js` les rend en PDF via le
  navigateur.
- **Pourquoi** : un document écrit à la main diverge du code en une journée. Généré, il suit les
  sources — et une valeur corrigée dans `docs/IA.md` se retrouve dans le dossier sans intervention.
- **Écarté** : un traitement de texte — impossible à régénérer, et les chiffres y vieillissent mal.

### La présentation est en Bento, exportée en `.pptx`

- **Quoi** : le deck de soutenance est un document Bento (`SENTINEL-X-G20.bento.html`) ; un
  convertisseur (`bento2pptx.py`) en produit un `.pptx` natif, texte modifiable.
- **Pourquoi** : Bento apporte le morph, les graphiques et les slides d'état, très au-dessus d'un
  diaporama de puces ; mais le rendu attendu est un `.pptx`, que le seul export PDF de Bento ne
  fournit pas.
- **Écarté** : un `.pptx` de captures d'écran — fidèle mais non modifiable ; renoncer au `.pptx` —
  contredit le rendu attendu.

### Le module `presence/` est hors du périmètre du sujet

- **Quoi** : le pointage du personnel (visage + geste du pouce) n'est pas documenté dans le README
  principal, qui renvoie vers `presence/README.md`.
- **Pourquoi** : ce module vient d'une **directive antérieure** au workshop. Le sujet SENTINEL-X
  demande la détection d'intrusion et la maintenance prédictive, pas le suivi des horaires — et la
  CNIL admet la biométrie pour le contrôle d'accès, pas pour le pointage.
- **Écarté** : supprimer le module — la vision s'en sert comme source de la liste blanche ; le
  laisser au premier plan — brouille le périmètre du rendu.

### Un seul dépôt, et la racine n'en est plus un

- **Quoi** : tout vit dans `Fortex/`. La racine de l'espace de travail n'est plus un dépôt Git, et
  `dev` et `infra` sont republiés depuis les sous-arbres.
- **Pourquoi** : il existait à la racine un dépôt sans aucun fichier suivi, mais avec deux commits
  d'avance dont un qui **supprimait `dashboard/`** — un `git push` aurait détruit le dépôt `dev`.
  Un dépôt qui ne suit rien n'est pas un dépôt.
- **Écarté** : nettoyer ce dépôt racine — un dépôt vide dont le seul effet possible est destructeur
  se supprime, il ne se répare pas.

### Les documents tiers ne sont pas versionnés

- **Quoi** : le sujet du workshop et les supports de formation IPSSI restent sur le disque dans
  `docs/reference/`, mais sont exclus par `.gitignore`.
- **Pourquoi** : ce ne sont pas nos documents, et les trois dépôts GitHub sont **publics**. Les
  rediffuser nous exposerait sans rien apporter au projet.
- **Écarté** : les versionner « puisqu'ils sont internes » — `Fortexworkshop/ia` est visible par
  n'importe qui ; un dépôt privé — le rendu doit rester consultable par le jury.
