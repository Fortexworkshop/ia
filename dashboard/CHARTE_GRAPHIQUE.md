# Charte graphique — Fortex

Les valeurs vivent dans [src/tokens.css](src/tokens.css). Ne jamais écrire une couleur ou une taille en dur dans un composant : utiliser le token.
Référentiel d'accessibilité : **RGAA 4.1** (niveau AA visé). Les rapports de contraste ci-dessous sont calculés (formule WCAG), ils ne remplacent pas un audit complet.

## Thèmes
Deux thèmes : sombre et clair. Par défaut, l'interface suit la préférence du système ; le bouton « Thème » de l'en-tête permet de choisir automatique, clair ou sombre (choix mémorisé dans le navigateur). Les composants n'utilisent que des tokens : seul `tokens.css` change entre thèmes.

## Couleurs et contrastes — thème sombre
| Rôle | Token | Valeur | Contraste sur `--surface` | Critère |
|---|---|---|---|---|
| Fond | `--bg` | #101418 | — | |
| Cartes | `--surface` / `--surface-2` / `--surface-3` | #1A2029 / #222A35 / #2A3340 | — | |
| Texte | `--text` | #F2F0EA | 14,4:1 | 3.2 (≥ 4,5:1) |
| Texte secondaire | `--text-muted` | #9AA4B2 | 6,5:1 (5,1:1 sur `--surface-3`) | 3.2 |
| Accent | `--accent` | #FF9E8A | 8,2:1 | 3.2 |
| Texte sur accent | `--on-accent` | #101418 | 9,3:1 sur l'accent | 3.2 |
| OK | `--ok` | #7DDC9A | 9,8:1 | 3.2 |
| Avertissement | `--warning` | #F4D35E | 11,2:1 | 3.2 |
| Critique | `--critical` | #FF6B6B | 5,9:1 (4,6:1 sur `--surface-3`) | 3.2 |
| Contour des commandes | `--control-border` | #6F7B8A | 3,8:1 | 3.3 (≥ 3:1) |

Séries de données, une teinte fixe par grandeur, volontairement distinctes de l'accent et des couleurs d'état : température `--series-temp` #C9A0FF (violet) · humidité `--series-hum` #7FB4FF (bleu) · gaz `--series-gas` #4FD1C5 (cyan) · présence `--series-presence` #E8E8E8 (gris clair). Toutes à plus de 7:1 sur `--surface` (critère 3.3, graphiques ≥ 3:1).

## Couleurs et contrastes — thème clair
Contrastes calculés (WCAG). Les textes et l'accent sont utilisés sur `--bg` et `--surface` ; les colonnes donnent ces deux fonds.

| Rôle | Token | Valeur | Sur `--bg` / `--surface` |
|---|---|---|---|
| Fond | `--bg` | #F6F4EF | — |
| Cartes | `--surface` / `--surface-2` / `--surface-3` | #FFFFFF / #F0EEE8 / #E4E1D9 | — |
| Texte | `--text` | #1B1F26 | 15,0:1 / 16,5:1 |
| Texte secondaire | `--text-muted` | #4B5563 | 6,9:1 / 7,6:1 (5,8:1 sur `--surface-3`) |
| Accent | `--accent` | #B8381F | 5,3:1 / 5,8:1 |
| Texte sur accent | `--on-accent` | #FFFFFF | 5,8:1 sur l'accent |
| OK / Avertissement / Critique | `--ok` / `--warning` / `--critical` | #17743A / #8A6100 / #B42318 | 5,3 / 5,0 / 6,0 : 1 sur `--bg` |
| Contour des commandes | `--control-border` | #6B7280 | 4,4:1 / 4,8:1 |
| Séries | température / humidité / gaz / présence | #7C3AED / #1D5FD1 / #0F766E / #374151 | ≥ 5,0:1 |

Limite : l'accent (#B8381F) ne doit pas servir de texte sur `--surface-3` (4,4:1, sous 4,5:1) ; il y sert seulement de fond de bouton avec `--on-accent`.

## Règles RGAA appliquées
- **Couleur jamais seule (3.1)** : un niveau d'alerte est écrit en toutes lettres (« critique », « avertissement ») en plus de la bordure colorée ; l'état d'un bouton est écrit (« Buzzer : activé ») et exposé par `aria-pressed` ; chaque courbe a un titre et un `aria-label`.
- **Contrastes (3.2, 3.3)** : voir le tableau. Tout texte d'interface ≥ 4,5:1, tout contour de commande ≥ 3:1.
- **Focus visible (10.7)** : contour de 2 px en `--accent`, décalé de 2 px, sur tous les éléments interactifs. Ne jamais le supprimer.
- **Texte redimensionnable (10.4)** : tailles en `rem` (13 → 0,8125 · 14 → 0,875 · 15 → 0,9375 · 20 → 1,25 · 26 → 1,625 · 34 → 2,125). Interligne 1,5. Mise en page fluide, sans défilement horizontal à 320 px.
- **Structure (9.1, 9.2, 12.6)** : un seul `h1`, titres hiérarchisés, landmarks `header`, `nav` (étiqueté), `main`.
- **Évitement (12.7)** : lien « Aller au contenu » en premier, visible au focus.
- **Navigation (12.x, 13.x)** : lien de la page courante marqué `aria-current="page"` et par un style non coloré (fond plein) ; liens soulignés.
- **Titre de page (8.5)** : `document.title` change à chaque page ; langue `fr` déclarée (8.3).
- **Messages d'état (7.5)** : alertes et journal de commandes dans une région `aria-live="polite"`.
- **Mouvement (13.8)** : aucune animation ; `prefers-reduced-motion` respecté par précaution.
- **Images (1.1)** : photo = `alt` avec le nom ; flux caméra avec `alt`.

## Typographie, espacements, formes
Une seule famille : pile système (`--font`). Tailles : 13, 14, 15, 20, 26, 34 px (en `rem`). Pas de 4 px (`--sp-1` à `--sp-6`). Cartes : rayon 14 px. Largeur de contenu : 1100 px.

## Principes graphiques
Deux thèmes, un seul accent (corail en sombre, rouge brique en clair), aplats sans dégradé ni ombre. Le deck [Bento](../Bento/Bento_Slides.bento.html) reprend fond, accent et police.

## Limites et points à valider
- Pas d'audit RGAA complet (lecteur d'écran, navigation clavier, zoom 200 %, test utilisateur) : à faire sur le rendu final.
- Le flux caméra et les photos n'ont pas d'alternative textuelle de contenu au-delà du nom (RGAA 4.1 : à définir pour un flux vidéo).
- Logo non défini. Le nom définitif est Fortex ; Sentinel-X reste le nom du sujet.
- Le thème clair n'a pas été vérifié visuellement dans un navigateur.
