# Charte graphique et UX — FORTEX Supervision

Les valeurs vivent dans [src/tokens.css](src/tokens.css). Aucune couleur ni taille en dur dans un composant.

## Intention

FORTEX surveille une micro-centrale isolée. L'utilisateur est un opérateur de supervision qui doit répondre en une seconde à « tout va bien ? », puis agir vite si ce n'est pas le cas. L'interface suit donc les principes d'une **IHM de conduite haute performance** (norme ISA-101), plutôt que ceux d'un tableau de bord marketing :

- **L'état normal est calme et neutre.** Gris, sans couleur vive. Une interface qui clignote en permanence n'alerte plus personne.
- **La couleur signale un écart, et seulement un écart.** Rouge : critique. Ambre : avertissement. Violet : liaison perdue. Le bleu acier est réservé à l'interaction (liens, sélection, focus) et n'est jamais une couleur d'état.
- **Hiérarchie de lecture.** Bandeau d'état du site, puis mesures, puis alarmes à traiter et actionneurs. L'action la plus urgente (couper le buzzer, voir les alarmes) est dans le bandeau.
- **Les données sont datées.** La fraîcheur de la dernière mesure est toujours visible. Au-delà de 10 s sans mesure, le site passe en « Liaison perdue » : des valeurs figées ne doivent jamais passer pour des valeurs en direct.
- **L'IA, le garde-fou et l'exercice sont distingués.** Chaque alarme indique son origine (IA prédictive, IA vision, garde-fou à seuil, exercice). Les alarmes d'exercice portent une étiquette en pointillés.
- **Sobriété de marque.** Le logo est un bastion en plan (le « fort » de FORTEX) autour d'un capteur. Pas de dégradé, pas d'ombre, pas d'animation décorative.

## Revue des éléments : pourquoi chacun est là (ou plus là)

Chaque élément doit aider l'opérateur à répondre à « que se passe-t-il, et que dois-je faire ? ». Revue faite le 2026-10-08.

| Élément | Décision | Raison |
|---|---|---|
| Bandeau d'état du site | **Gardé, corrigé** | Il affirmait « toutes les mesures sont dans leur profil habituel » sans le savoir : l'IA prédictive ne remonte pas son état. Il dit maintenant « Aucune alarme » et ne cite que ce qui est vérifié. Il passe en « Vigilance » si la vision est arrêtée, si la liaison MQTT ou la base tombe. Au chargement, il dit « Connexion en cours » et non « Liaison perdue ». |
| Chaîne de surveillance | **Ajouté** (vue par défaut) | Absence majeure : sans elle, « aucune alarme » ne prouvait rien, car une IA arrêtée ne lève aucune alarme. Il couvre aussi le « statut du boîtier » demandé par le sujet. L'IA prédictive y est affichée « Non supervisé », faute de signal du serveur. |
| Tuiles capteurs | **Gardées, corrigées** | « Dans le profil habituel » était une affirmation non fondée : remplacée par « Aucune alarme ». |
| Tuile Mouvement | **Refaite** | Une courbe 0/1 n'apprend rien. Elle affiche maintenant l'heure du dernier mouvement. |
| Alarmes à traiter | **Gardé** (deuxième position) | C'est l'action principale de l'opérateur. Acquitter demande la connexion opérateur. |
| Actionneurs | **Gardés** | Exigés par le sujet. Désactivés hors session opérateur. |
| Mode exercice | **Retiré de la vue par défaut**, reste au catalogue | Un bouton qui déclenche une alarme critique n'a pas sa place sur l'écran opérationnel (risque de fausse manœuvre). Réservé à l'opérateur. |
| Consignes de poste | **Gardé, mention ajoutée** | Une consigne locale peut être prise pour une consigne partagée : le widget indique « enregistrée sur ce poste uniquement ». |
| Personnes sur site, Présence, Individus | **Gardés, protégés** | Utiles en cas d'évacuation et pour éviter de fausses alertes intrusion sur le personnel. Données personnelles et biométriques : connexion opérateur requise, effacées de la mémoire à la déconnexion. **Point ouvert, voir ci-dessous.** |
| Caméra | **Gardée, sécurisée, fiabilisée** | Exigée par le sujet. Arrêter la vision demande une confirmation et met le site en « Vigilance ». Le flux distingue « arrêtée », « arrêtée sur une erreur (code) », « démarrage », « image figée » et « injoignable » ; il se reconnecte seul. |
| Fonction d'une personne | **Supprimée** | Elle ne servait à rien à l'opérateur. Retirée du formulaire, de l'API et de l'incrustation sur la vidéo. |
| Lien vers Grafana | **Ajouté** (si `VITE_GRAFANA_URL` est défini) | Absence : le dashboard ne garde que 4 minutes de mesures, l'historique long est dans Grafana. |
| Connexion opérateur | **Ajouté** | Le code ne pouvait pas rester compilé dans le JavaScript (OWASP A07). |
| Horloge, état de la liaison (barre du haut) | **Gardés** | Visibles sur toutes les pages, alors que le bandeau n'est que sur la vue d'ensemble. L'heure sert de référence pour dater les événements. |
| Sélecteur de thème | **Gardé** | Préférence d'accessibilité (sensibilité à la lumière, lecture en plein jour). Réduit à une icône sur mobile. |

**Point ouvert (équipe et coachs).** Le pointage des horaires par reconnaissance faciale relève du contrôle du temps de travail. Le règlement type biométrie de la CNIL (2019) n'autorise la biométrie que pour le contrôle d'accès aux locaux, pas pour le contrôle des horaires. Garder la reconnaissance pour la liste blanche anti-intrusion est défendable. Le pointage par geste mérite d'être présenté comme démonstration technique, ou retiré de la démo.

**Absences assumées.**
- Pas d'alarme sonore dans le navigateur : le buzzer du boîtier joue ce rôle, et un son automatique contreviendrait à WCAG 1.4.2 sans contrôle.
- Pas de commentaire à l'acquittement : utile, mais sans compte nominatif, il ne serait pas attribuable.

## Vue d'ensemble personnalisable

Chaque poste organise sa vue d'ensemble : ajouter, supprimer, régler (titre, taille, réglages propres), déplacer et réorganiser les éléments. La disposition est mémorisée dans le navigateur du poste.

- **Mode « Personnaliser » explicite.** En usage normal, aucune poignée ni outil d'édition n'est affiché : l'écran reste calme. En mode édition, les cadres passent en pointillés.
- **Le bandeau d'état du site est hors de la grille.** Il ne peut être ni supprimé ni déplacé : on ne masque pas une alarme par une mauvaise manipulation.
- **Déplacer sans glisser** (RGAA 7.1, WCAG 2.5.7). Chaque élément a des boutons « Déplacer avant / après » utilisables au clavier et au doigt. Le glisser-déposer par la poignée n'est qu'un raccourci à la souris. Chaque déplacement est annoncé (« Température déplacé en position 2 sur 7 ») et le focus reste sur le bouton utilisé.
- **Suppression réversible.** « Annuler » reçoit le focus juste après la suppression. « Disposition par défaut » demande confirmation.
- **Catalogue** en `<dialog>` native : le focus y est piégé et Échap ferme. Types disponibles : capteur, alarmes à traiter, actionneurs, personnes sur site, caméra, consignes de poste, mode exercice.
- **Tailles** : petit (3/12), moyen (6/12), pleine largeur. Sous 75rem, un petit élément prend la demi-largeur. Sous 40rem, tous les éléments prennent la pleine largeur.

## Couleurs et contrastes (calculés, formule WCAG)

| Rôle | Token | Sombre | Clair | Contraste minimal mesuré |
|---|---|---|---|---|
| Fond | `--bg` | #0D1117 | #F3F4F6 | — |
| Panneaux | `--surface` / `-2` / `-3` | #151B23 / #1B222C / #242C38 | #FFFFFF / #F6F7F9 / #E8EBEF | — |
| Texte | `--text` | #E6E9EE | #141820 | 11,6:1 / 14,9:1 |
| Texte secondaire | `--text-muted` | #A4ADBA | #48515E | 6,2:1 / 6,7:1 |
| Légendes | `--text-faint` | #8A94A3 | #5B6574 | 4,6:1 / 4,9:1 |
| Interaction | `--accent` | #79AAF7 | #1D5BC6 | 6,0:1 / 5,2:1 |
| Critique | `--critical` | #FF6B66 | #B3261E | 5,1:1 / 5,5:1 |
| Avertissement | `--warning` | #F2B440 | #8A5300 | 7,6:1 / 5,3:1 |
| Normal confirmé | `--ok` | #5FCF95 | #17703F | 7,3:1 / 5,1:1 |
| Liaison perdue | `--stale` | #C3A6FF | #5B3CC4 | 6,9:1 / 6,1:1 |
| Contours de commandes | `--border` | #6B7686 | #6F7A89 | 3,1:1 / 3,6:1 |

Les contrastes minimaux sont mesurés sur le fond le moins favorable des quatre surfaces. Chaque couleur d'état garde au moins 5,3:1 sur son propre fond teinté (`--critical-bg`, etc.).

## Typographie et espacements

- Pile système uniquement : aucune police à télécharger (LCP) et aucun changement de police à l'affichage (CLS). Chiffres tabulaires partout, pour que les valeurs ne bougent pas en changeant.
- Tailles en `rem` : 13, 14, 16 (texte), 20, 26 et 40 px (valeurs de capteurs).
- Espacements : pas de 4 px. Cibles cliquables d'au moins 44 px.

## Accessibilité : WCAG 2.2 AA et RGAA 4.1

| Critère RGAA | Mise en œuvre |
|---|---|
| 1.2, 1.3 (images) | Icônes décoratives (`aria-hidden`). Les courbes ont leur équivalent en texte : tendance, minimum et maximum. |
| 3.1 (couleur) | Niveau d'alarme écrit, icône de forme différente (octogone pour critique, triangle pour avertissement), interrupteurs avec état écrit. |
| 3.2, 3.3 (contrastes) | Voir le tableau. Textes ≥ 4,5:1, contours ≥ 3:1. |
| 7.1, 7.5 (scripts, messages d'état) | Nouvelle alarme annoncée par une région `role="alert"`. Changement d'état du site par `role="status"`. Le détail qui change chaque seconde n'est pas annoncé. |
| 8.3, 8.5, 8.6 (langue, titre) | `lang="fr"`. Le titre du document change à chaque page. |
| 9.1 (titres) | Un `h1` par page, puis des `h2`. |
| 10.4, 10.11 (zoom, reflow) | Tailles en `rem`, mise en page fluide jusqu'à 320 px. |
| 10.7 (focus) | Contour de 3 px en couleur d'interaction sur tous les éléments focusables. |
| 11.1, 11.2, 11.10 (formulaires) | Étiquettes liées, aides (`aria-describedby`), champs obligatoires signalés, erreur annoncée et focus sur le champ fautif. |
| 12.6, 12.7 (navigation) | Zones `header`, `nav` (étiquetée) et `main`. Lien d'évitement en premier. Focus déplacé sur le contenu à chaque changement de page. |
| 13.8 (mouvement) | Aucune animation décorative. `prefers-reduced-motion` respecté. |

### Critères ajoutés par WCAG 2.2 (au-delà du RGAA 4.1, basé sur WCAG 2.1)

| Critère WCAG 2.2 | Niveau | Mise en œuvre |
|---|---|---|
| 2.4.11 Focus non masqué | AA | `scroll-padding-top` : un élément focalisé n'est jamais caché sous la barre du haut collante. La barre n'est collante que sur grand écran. |
| 2.5.7 Mouvements de glissement | AA | Chaque glisser-déposer a son équivalent en un clic (boutons « Déplacer avant / après »). |
| 2.5.8 Taille de cible | AA | Cibles d'au moins 36 px (44 px pour les commandes principales). Les liens isolés ont une zone d'au moins 28 px. |
| 3.2.6 Aide cohérente | A | Aide contextuelle placée toujours au même endroit (sous le champ concerné). Pas de mécanisme d'aide global. |
| 3.3.7 Saisie redondante | A | Le code opérateur n'est demandé qu'une fois par onglet. Modifier une personne pré-remplit le formulaire. |
| 3.3.8 Authentification accessible | AA | Aucun test cognitif. Collage autorisé, `autocomplete="current-password"` avec un identifiant implicite pour les gestionnaires de mots de passe, bouton « Afficher ». |
| 4.1.1 Analyse syntaxique | — | Retiré de WCAG 2.2 (obsolète). |

**Vérifié** : axe-core (règles WCAG 2.2 A et AA) sur les 5 pages, thèmes sombre et clair, en situation d'alarme, en mode personnalisation, réglages ouverts, catalogue ouvert, connexion (avec erreur) et session opérateur : 0 violation. Ordre de tabulation, lien d'évitement et focus après navigation contrôlés au clavier.

**Pas vérifié** : lecteurs d'écran réels (NVDA, VoiceOver), zoom 200 % à la main, test avec des utilisateurs. Un outil automatique couvre environ un tiers des critères RGAA, ces résultats ne valent pas un audit.

## Sécurité

Détail par catégorie de l'OWASP Top 10:2025 dans [docs/SECURITE.md](../../docs/SECURITE.md) (§ 7). Côté interface : CSP stricte générée au build (`vite.config.js`), code opérateur saisi et jamais compilé, messages serveur validés (`src/data/validate.js`), échecs toujours affichés (`src/components/Feedback.jsx`), widget en erreur isolé (`ErrorBoundary`).

## Performance : Core Web Vitals

| Mesure | Seuil « bon » | Mesuré en laboratoire (CPU ralenti 4×, 4G lente, mobile) |
|---|---|---|
| LCP | ≤ 2,5 s | 1,6 s (vue d'ensemble), 1,7 s (alarmes) |
| CLS | ≤ 0,1 | 0,001 (simulateur), 0,002 à 0,006 (serveur réel) |
| INP | ≤ 200 ms | 24 ms |

Ce qui les tient :

- **LCP.** Pas de police web. Fond critique en ligne dans `index.html`. Seule la vue d'ensemble est dans le paquet principal, les autres pages sont chargées à la demande (`React.lazy`).
- **CLS.** Hauteurs réservées (barre du haut, bandeau d'état, tuiles, courbes). Sur mobile, le bandeau garde la même hauteur quel que soit l'état, et il affiche « Connexion en cours » (et non « Liaison perdue ») avant la première mesure. Cadre vidéo au format 4:3 fixe. Chiffres tabulaires. Thème appliqué avant le premier affichage.
- **INP.** Une seule connexion WebSocket partagée (`state/live.jsx`). L'horloge et la fraîcheur des données ne re-rendent que leurs composants. Acquittement affiché immédiatement, avant la réponse du serveur.

Mesure sur le terrain : `src/vitals.js` collecte LCP, CLS et INP dans `window.__vitals`, et les affiche dans la console en développement ou avec `?vitals` dans l'URL.
