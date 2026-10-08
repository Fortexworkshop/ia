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

## Accessibilité : RGAA 4.1, niveau AA visé

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

**Vérifié** : axe-core (règles WCAG 2.2 A et AA) sur les 5 pages, thèmes sombre et clair, et en situation d'alarme : 0 violation. Ordre de tabulation, lien d'évitement et focus après navigation contrôlés au clavier.

**Pas vérifié** : lecteurs d'écran réels (NVDA, VoiceOver), zoom 200 % à la main, test avec des utilisateurs. Un outil automatique couvre environ un tiers des critères RGAA, ces résultats ne valent pas un audit.

## Performance : Core Web Vitals

| Mesure | Seuil « bon » | Mesuré en laboratoire (CPU ralenti 4×, 4G lente, mobile) |
|---|---|---|
| LCP | ≤ 2,5 s | 1,4 s (vue d'ensemble), 1,5 s (alarmes) |
| CLS | ≤ 0,1 | 0,002 |
| INP | ≤ 200 ms | 24 ms |

Ce qui les tient :

- **LCP.** Pas de police web. Fond critique en ligne dans `index.html`. Seule la vue d'ensemble est dans le paquet principal, les autres pages sont chargées à la demande (`React.lazy`).
- **CLS.** Hauteurs réservées (barre du haut, bandeau d'état, tuiles, courbes). Cadre vidéo au format 4:3 fixe. Chiffres tabulaires. Thème appliqué avant le premier affichage.
- **INP.** Une seule connexion WebSocket partagée (`state/live.jsx`). L'horloge et la fraîcheur des données ne re-rendent que leurs composants. Acquittement affiché immédiatement, avant la réponse du serveur.

Mesure sur le terrain : `src/vitals.js` collecte LCP, CLS et INP dans `window.__vitals`, et les affiche dans la console en développement ou avec `?vitals` dans l'URL.
