# Guide de méthodologie rigoureuse — projet d'équipe

Construit à partir des leçons tirées d'un projet solo précédent
(PagesLibres), complétées par des pratiques supplémentaires nécessaires
dès qu'un projet passe à plusieurs personnes et touche au mobile — deux
dimensions qu'un projet solo web n'exige pas.

---

## 1. Planification et cadrage

- Écrire le périmètre fonctionnel **et** le hors-périmètre dès le départ,
  noir sur blanc. Un hors-périmètre écrit est plus facile à défendre en
  cours de route qu'une limite qu'on découvre en se laissant déborder.
- Objectifs mesurables (SMART) plutôt que des intentions vagues — « F3
  doit permettre de pointer en moins de 10 secondes » plutôt que « le
  pointage doit être rapide ».
- Table des risques dès le cadrage, avec une mesure par risque — pas pour
  se couvrir, mais parce qu'un risque écrit se traite, un risque implicite
  se découvre en catastrophe.

## 2. Modéliser avant de coder

- Modéliser les données **avant** d'écrire la première entité de code.
  Un schéma qui change après coup coûte toujours plus cher qu'un schéma
  corrigé sur le papier.
- Relire le cahier des charges et le modèle de données **l'un contre
  l'autre**, pas seulement chacun pour soi — c'est ce croisement qui
  révèle les contradictions (une exigence promise au cadrage mais absente
  du schéma, ou l'inverse), pas la relecture isolée de chaque document.
- Toute contrainte réglementaire (RGPD, droit du travail si c'est un
  contexte entreprise) doit se traduire en contrainte de schéma dès la
  modélisation — anonymisation, durée de conservation des données de
  présence, pas ajoutée en fin de projet.

## 3. Git et collaboration (spécifique au travail à plusieurs)

- Aucune fusion directe sur `main`/`develop` sans Pull Request **relue
  par quelqu'un d'autre que l'auteur**. Une auto-validation, aussi
  rigoureuse soit-elle, ne remplace pas un second regard.
- Convention de commits partagée (Conventional Commits ou équivalent),
  décidée une fois, documentée, appliquée par tous.
- Jamais de réécriture d'historique (`rebase -i`, changement de dates de
  commit, force-push) sur une branche que d'autres ont déjà récupérée,
  sans prévenir et sans validation explicite de l'équipe — un incident de
  ce type peut désynchroniser le dépôt de tout le monde, pas seulement le
  vôtre.
- Un gabarit de Pull Request avec une checklist minimale : tests ajoutés
  ou mis à jour, pas de secret committé, CI verte avant de demander une
  relecture.

## 4. Sécurité — pensée dès la conception, spécifique au pointage

Au-delà de l'OWASP Top 10 générique (injection, XSS, CSRF, authentification
— à couvrir comme pour tout projet), une application de présence a des
risques de fraude propres au domaine, à anticiper dès la conception plutôt
qu'après un incident :

- **Usurpation de présence** (« pointer pour quelqu'un d'autre ») : si le
  pointage repose sur un appareil, lier le pointage à une session
  authentifiée sur cet appareil, pas seulement à une saisie libre d'identité.
- **Falsification de position** (GPS spoofing) si le pointage est
  géolocalisé : un pointage géolocalisé ne doit jamais être considéré
  comme une preuve absolue — envisager une détection de cohérence
  (vitesse de déplacement implausible entre deux pointages, par exemple)
  plutôt que de faire une confiance aveugle aux coordonnées reçues.
- **Rejeu d'un code** (QR code photographié et réutilisé) si le pointage
  repose sur un QR code : envisager un code à usage unique ou à durée de
  vie courte plutôt qu'un code statique par session.
- Ces trois risques doivent être nommés dans le cadrage (section 1 de la
  directive de lancement), pas découverts après un signalement d'abus.

## 5. Tests et CI dès le premier commit

- CI (lint + build) configurée avant la première fonctionnalité, pas en
  cours de projet — une CI qui arrive tard rate souvent ses propres
  erreurs de configuration faute d'avoir été testée tôt sur du code réel.
- Un test de bout en bout sur le parcours critique (un participant pointe,
  l'organisateur voit la présence) vaut mieux que de nombreux tests
  isolés sur des fonctions annexes.
- Vérifier le déclenchement réel de la CI sur chaque branche protégée
  (`main` et `develop`), pas seulement sur une branche de travail — un
  pipeline qui ne se déclenche pas sur la bonne branche est un défaut
  classique qui passe inaperçu tant que personne ne vérifie explicitement.

## 6. Vérification indépendante systématique — la règle la plus rentable

Ne jamais accepter un rapport (d'un coéquipier ou d'un agent) sur la seule
base de sa déclaration :

- Un lien de CI donné comme « vert » : ouvrir le lien soi-même.
- Un commit donné comme poussé : vérifier le hash sur le dépôt distant,
  pas seulement en local.
- Une mesure de sécurité donnée comme « en place » : la tester en situation
  réelle (une vraie tentative, pas une relecture de configuration) —
  certains défauts de sécurité restent invisibles à la seule lecture du
  code et ne se révèlent qu'à l'usage réel.
- Un silence sur un point demandé n'est pas une confirmation — si un
  rapport ne mentionne pas un point explicitement demandé, le considérer
  non fait tant que ce n'est pas confirmé, pas supposé fait.

## 7. Documentation continue

- Le `README.md` et la procédure de déploiement se rédigent au fur et à
  mesure, pas en fin de projet — un projet qui reporte sa documentation à
  la fin la reporte généralement indéfiniment.
- Chaque décision technique structurante consignée dans `DECISIONS.md`
  au moment où elle est prise, en 3-4 lignes (quoi, pourquoi, options
  écartées) — pas reconstituée de mémoire des mois plus tard.

## 8. Spécificités mobile (React Native) — absentes d'un projet web

- **Fragmentation des appareils** : tester sur plusieurs versions
  d'Android et d'iOS, pas seulement sur l'émulateur de développement par
  défaut.
- **Permissions sensibles** (localisation, notifications) : prévoir dès
  la conception le texte de justification affiché à l'utilisateur, requis
  par les stores — une permission de géolocalisation en arrière-plan sans
  justification claire peut faire rejeter l'application en revue.
- **Mode hors-ligne** : si le pointage doit fonctionner sans connexion
  (cf. section 2 de la directive de lancement), concevoir la
  synchronisation différée dès le modèle de données (horodatage de
  création vs horodatage de synchronisation), pas en rustine après coup.
- **Délai de revue des stores** (Apple App Store notamment) : à intégrer
  dans le planning comme une dépendance externe non négociable, au même
  titre qu'une API tierce — prévoir des cycles de publication en
  conséquence, pas une mise en production à la dernière minute.
- **Déploiement progressif** : canal interne/bêta (TestFlight, Internal
  App Sharing) avant publication publique, à chaque version.

## 9. Gestion des secrets et configuration

- `.env.example` sans valeur réelle, présent dès le premier commit.
- Vérification de l'absence de secret dans l'historique Git complet avant
  chaque publication, pas seulement dans l'état courant du dépôt — un
  secret supprimé d'un commit récent reste compromis s'il existe encore
  dans un commit plus ancien.
- Toute clé API tierce utilisée côté client (donc visible dans le binaire
  de l'application mobile) doit être restreinte côté fournisseur
  (domaine, bundle ID, quota) — une variable d'environnement ne la rend
  pas secrète, elle évite seulement de la committer.

## 10. Revue de code entre pairs — le vrai ajout du travail en équipe

- Une Pull Request n'est prête à relire que si la CI est verte et que
  l'auteur a lui-même relu son propre diff avant de solliciter quelqu'un
  d'autre.
- Le relecteur vérifie trois choses au minimum : la logique correspond-elle
  à la tâche décrite, les cas d'erreur sont-ils gérés, un secret ou une
  régression de sécurité se serait-il glissé dans le diff.
- Un désaccord de revue se résout par la discussion sur la Pull Request,
  pas par une fusion forcée — si le désaccord persiste, il remonte à
  l'équipe plutôt que de rester entre deux personnes.
