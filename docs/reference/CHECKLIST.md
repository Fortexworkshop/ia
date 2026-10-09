# Checklist FORTEX / SENTINEL-X

État au 2026-10-08. Référence : sujet officiel (`Workshop-2026_BAC+4_Sujet_Sentinel-X.pdf.pdf`).

## Périmètre accepté par le workshop

- Prototype **virtuel** (boîtier simulé) à la place du boîtier physique : pas de matériel distribué.
- Coque **non fabriquée** (CAO Fusion360, impression 3D, gravure laser).
- Pentest croisé du jeudi **supprimé** (donc pas de rapport d'audit post-pentest).

## Fait

- [x] API REST et WebSocket, avec `POST /api/v1/alerts` (115 tests)
- [x] Dashboard : courbes en temps réel, statut du boîtier, flux webcam, commande buzzer et LED
- [x] Firmware ESP8266 en C++ (écrit ; jamais exécuté sur du matériel)
- [x] Boîtier virtuel, même protocole MQTTS que le firmware
- [x] Vision YOLOv8 : 640×480, 32 ms mesurés (exigence : moins de 100 ms)
- [x] Maintenance prédictive Isolation Forest, seuil appris
- [x] Docker-Compose : PostgreSQL, Mosquitto, backend, Prometheus, Grafana
- [x] MCO : CPU, RAM, journaux MQTT, via Grafana
- [x] MQTTS avec comptes et droits, conteneurs durcis, secrets hors Git
- [x] Dashboard : WCAG 2.2 / RGAA, OWASP Top 10 2025, Core Web Vitals
- [x] Documents sources du dossier : `docs/IA.md`, `docs/SECURITE.md`, `firmware/README.md` (câblage)

## À faire

### Dossier PDF (`Workshop2026-M1-G<n>-Dossier.pdf`)

- [ ] Schéma réseau (sous-réseau, flux, ports)
- [ ] Schéma de câblage au format image (aujourd'hui, du texte)
- [ ] Assemblage en un seul PDF : schémas, matrice de sécurité, doc IA
- [ ] Poster A3 en annexe

### Infra

- [ ] Topologie de table : point d'accès Wi-Fi, plan d'adressage, isolation (aujourd'hui seulement `192.168.10.0/24` dans les règles de pare-feu)
- [ ] Variante Windows du durcissement : expliquer pourquoi le pare-feu Windows remplace UFW (le sujet suppose Linux, le serveur est sous Windows 11). Appliquer les règles de `docs/SECURITE.md` sur le PC W11 et garder la preuve avec `check_security.py`.
- [ ] Vérifier la stack complète sur le PC W11 (`setup.ps1` puis `start.ps1`) : jamais exécutés depuis le laptop Fedora

### Marketing et soutenance

- [ ] Teaser 60 s en 9:16, H.264, sur fond vert : boîtier virtuel, dashboard, détection YOLO (pas de boîtier imprimé à montrer)
- [ ] `Workshop2026-M1-G<n>-Pres.pptx` (le deck Bento est un compte-rendu, pas ce rendu)
- [ ] Préparer le chrono de 10 min : 1 min présentation, 1 min teaser, 3 min démo live, 5 min pitch et Q&A

### Code et dépôt

- [ ] Passe sur le README : il mélange le projet avec un module de pointage de présence (`presence/`, ex-directive) ; à réduire au périmètre du sujet
- [ ] Ajouter `DECISIONS.md` et `CONTRIBUTING.md` (exigés par le guide de méthodologie)
- [ ] Zip final : `Workshop2026-M1-G<n>-Code.zip`

## À vérifier (risques)

- [ ] Le firmware compile-t-il ? La doc l'affirme, non contrôlé.
- [ ] Vision sur une vraie webcam : sur le laptop de dev, elle plante faute d'`ultralytics` installé
- [ ] Pointage par geste (reconnaissance faciale) : à trancher avec les coachs (la CNIL admet la biométrie pour le contrôle d'accès, pas pour les horaires)
- [ ] Seuils fixes (garde-fou à 40 °C, 600 de gaz) : préparer la réponse du jury, le sujet interdit les conditions statiques pour la maintenance prédictive
- [ ] `POST /api/v1/alerts` ne reçoit que les alertes de l'IA ; les capteurs passent par MQTT. Préparer l'explication.
- [ ] Limites connues à annoncer : dashboard et API en HTTP, flux caméra (`:8081/video`) sans authentification, code opérateur partagé
