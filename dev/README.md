# FORTEX Supervision — dashboard

Interface de conduite du site **SENTINEL-X** : mesures des capteurs, alarmes, vision, présence et
commande du boîtier. Elle interroge le PC serveur local en REST et reçoit le temps réel par une
unique connexion WebSocket.

> C'est le dépôt **`Fortexworkshop/dev`**. Le projet complet — firmware, backend, IA, infra — est
> dans **[`Fortexworkshop/ia`](https://github.com/Fortexworkshop/ia)**, où ce dossier est intégré
> comme sous-arbre.

## Démarrer

```bash
cd dashboard
pnpm install
pnpm dev            # http://localhost:5173 — développement, HMR
pnpm build          # build de production dans dist/
pnpm demo           # build + preview : en-têtes de sécurité et CSP, ce que lance start.ps1
```

Sans variable d'environnement, le dashboard tourne sur son **simulateur intégré** : il s'affiche et
s'anime seul, sans backend ni boîtier.

## Architecture

```
src/
├── main.jsx            point d'entrée
├── state/
│   ├── live.jsx        LiveProvider / useLive : LA connexion temps réel du poste
│   └── model.js        vocabulaire métier : libellés, origine des alarmes, état du site
├── data/               accès aux données : api.js, http.js, auth.js, validate.js, simulator.js
├── dashboard/          vue d'ensemble personnalisable : widgets.jsx, layout.js, WidgetGrid.jsx
├── components/         briques d'interface (SiteState, Alarm, CameraFeed, Sparkline…)
├── pages/              Alarms, Camera, Overview, People, Presence
└── tokens.css          toutes les couleurs et toutes les tailles
```

Quatre règles structurent le code :

- **Une seule connexion temps réel.** `src/state/live.jsx` reçoit tous les messages et les pages
  lisent cet état via `useLive`. Aucune page ne recrée sa propre source. `LiveProvider` interroge
  aussi `/health`, `/api/v1/vision` et `/api/v1/devices` toutes les 5 s.
- **Le modèle ne dit que ce qui est vérifié.** `src/state/model.js` ne doit rien affirmer que le
  serveur ne remonte pas : faute de signal de vie, l'IA prédictive est « Non supervisé ».
  Au-delà de 10 s sans mesure, le site passe en « Liaison perdue ».
- **Le contrat est partagé.** `data/simulator.js` et `data/api.js` exposent la même interface
  (`subscribe` / `sendCommand` / `inject`), et `data/validate.js` filtre **tout** message WebSocket
  avant qu'il n'atteigne le réducteur. Toute évolution du format doit rester compatible avec
  `backend/messages.py`, qui le produit.
- **Le paquet principal reste léger.** Seule la vue d'ensemble est chargée d'emblée ; les autres
  pages passent par `React.lazy`. `src/vitals.js` mesure LCP, CLS et INP (console avec `?vitals`).

La vue d'ensemble est **personnalisable par poste** : `dashboard/widgets.jsx` est le registre des
types d'éléments, `dashboard/layout.js` la disposition (opérations pures, `localStorage` clé
`fortex.layout.v1`), `dashboard/WidgetGrid.jsx` le mode édition. Le bandeau d'état du site en est
volontairement exclu : on ne masque pas une alarme par une mauvaise manipulation. Le
glisser-déposer est doublé de boutons « Déplacer avant / après », obligatoires pour le RGAA.

## Configuration

Le dashboard lit quatre variables, documentées dans
[`dashboard/.env.example`](dashboard/.env.example) et écrites par `scripts/configure.py` :

| Variable | Rôle |
|---|---|
| `VITE_API_URL` | URL du backend REST + WebSocket. **Vide = simulateur intégré.** |
| `VITE_CAMERA_URL` | Flux MJPEG du PC serveur. Vide = page caméra sans flux. |
| `VITE_GRAFANA_URL` | Grafana, pour l'historique long. Vide = lien masqué. |
| `VITE_DASHBOARD_TOKEN` | **Toujours vide** (voir ci-dessous). |

## Sécurité

- **Le code opérateur n'est jamais compilé dans le JavaScript.** Une variable `VITE_*` finit dans
  le bundle, donc lisible par quiconque ouvre la page (OWASP A07). Le code est saisi dans
  « Connexion opérateur », gardé en `sessionStorage` (`src/data/auth.js`) et effacé à la
  déconnexion.
- **Tout appel HTTP passe par `src/data/http.js`**, qui remonte les erreurs à l'interface et traite
  un `401` comme une fin de session.
- **La CSP est générée au build** par `vite.config.js`, avec les empreintes SHA-256 des blocs en
  ligne de `index.html`. Un nouveau script ou style en ligne serait bloqué.

## Conception

L'interface suit **ISA-101** : l'état normal est neutre, et la couleur ne signale qu'un écart. Le
bleu acier est réservé à l'interaction et n'est jamais une couleur d'état. Les objectifs
d'accessibilité sont RGAA 4.1 AA et WCAG 2.2 AA.

Couleurs, contrastes calculés, revue de chaque élément et critères d'accessibilité :
**[`dashboard/CHARTE_GRAPHIQUE.md`](dashboard/CHARTE_GRAPHIQUE.md)**. Toute couleur ou taille
s'ajoute dans `dashboard/src/tokens.css`, jamais en dur dans un composant.
