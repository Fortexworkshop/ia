# Compte-rendu — Workshop 2026 M1 (Sentinel-X)

Date : 2026-10-07 · Statut : chaîne complète fonctionnelle, projet publié.

## Décisions prises
- **Option B** : le portable d'un apprenant est le PC serveur local. Le boîtier ESP8266 est **simulé** pour la démo : mêmes topics, même compte MQTTS, même alarme locale. À confirmer avec les coachs : le sujet impose le boîtier et son rendu Fablab.
- **Backend Python** : FastAPI (REST + WebSocket), Mosquitto, PostgreSQL, le tout en Docker.
- **Dashboard React web** (Vite), thèmes clair et sombre, contrastes conformes RGAA AA.
- Un seul dépôt : les dépôts `infra` et `dev` y sont intégrés par `git subtree`.

## Réalisé
- **Dashboard** (`Fortex/dev/dashboard`) : Supervision (4 séries temps réel, commandes buzzer et LED, alertes), Individus, Présence, Caméra, pilotage de la vision, thèmes clair et sombre. Charte dans `CHARTE_GRAPHIQUE.md` et `tokens.css`.
- **Backend** (`Fortex/backend`) : REST + WebSocket (`:8080`), pont MQTT, PostgreSQL avec repli mémoire, alertes, commandes, liste des individus, journal de présence.
- **Infra** (`Fortex/infra`) : Mosquitto en MQTTS (`:8883`, deux comptes, anonyme refusé, ACL), PostgreSQL, backend conteneurisé et durci, génération des certificats et des comptes ; `scripts/check_security.py` couvre 7 contrôles.
- **IA** (`Fortex/sentinel`, `presence`) : vision YOLOv8n à **32 ms par trame** (exigence < 100 ms) et maintenance prédictive Isolation Forest à **seuil appris** — 50 incidents détectés sur 50, 1 fausse alerte sur 50, **436 s d'avance** sur le seuil critique. Le `SafetyAlarm` à seuil dur reste un garde-fou distinct de l'IA.
- **Présence et individus** : liste blanche gérée depuis le dashboard, empreinte partagée avec la vision `--whitelist` ; pointage par geste (pouce en haut = entrée, pouce de côté = pause puis reprise, pouce en bas = sortie).
- **Qualité** : 90 tests passent (1 ignoré) ; latence des gestes contenue sous 100 ms en ne détectant la main qu'une image sur deux.
- **Publié** : `github.com/Fortexworkshop/ia`, branche `dev`.

## Écart à résoudre
`DIRECTIVE_Lancement.md` décrit une appli de pointage qui ne correspond pas à Sentinel-X. Décider de l'abandonner ou de la réinterpréter ; ses pratiques d'équipe restent utiles.

## Points ouverts
1. **Boîtier** : garde-t-on le boîtier virtuel pour la démo, et que devient le rendu Fablab (CAO, impression, gravure) ?
2. **Chiffrement** : la stack MQTTS existe, mais la démo locale tourne encore en clair, sans jeton. À activer et à vérifier.
3. **RGPD** : seules les empreintes sont conservées et l'effacement est possible ; durée de conservation et accès restent à cadrer.
4. Périmètre exact de la « plateforme de test ».
5. **Automatisation** : le dépôt existe, mais la CI, `CONTRIBUTING.md` et `DECISIONS.md` ne sont pas en place.

## Prochaines étapes
1. Activer le chiffrement : générer certificats et comptes, repasser les 7 contrôles de sécurité.
2. Automatiser : CI lint + build, `CONTRIBUTING.md`, `DECISIONS.md`, branches protégées.
3. Cadrer : périmètre F1…Fn, hors-périmètre, risques, modèle de données.
4. Répéter la démo en direct : surchauffe lente, fuite de gaz, intrusion.
