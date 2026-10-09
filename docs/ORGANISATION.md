# Organisation de l'espace de travail

Dernière mise à jour : 2026-10-09 · Périmètre : l'espace de travail entier.

Ce document décrit **où vit quoi, et pourquoi**. Le plan de réorganisation du 9 octobre 2026 qui a
mené à cet état, son journal et ses vérifications sont dans l'historique Git :

```bash
git log -- docs/ORGANISATION.md docs/REORGANISATION.md   # ce document, puis son plan d'origine
```

---

## 1. Un seul dépôt

`Workshop2026-M1/` est l'espace de travail (disque, configuration de l'éditeur) ; **`Fortex/` est
le dépôt**. Rien n'est versionné à côté de lui.

| | `Workshop2026-M1/` | `Fortex/` |
|---|---|---|
| Dépôt | aucun | `Fortexworkshop/ia`, branche `dev` |
| Rôle | espace de travail, `.vscode/` | le projet |

> **L'ancien dépôt racine a été retiré, et ne doit pas être recréé.** Il pointait sur
> `Fortexworkshop/dev` tout en ne suivant **aucun fichier**, avec deux commits d'avance dont un
> qui **supprimait `dashboard/`** : un `git push` depuis la racine aurait effacé le dashboard du
> dépôt `dev`.

---

## 2. Arborescence

```
Workshop2026-M1/
├── .vscode/mcp.json              configuration de l'espace VS Code (serveur MCP)
└── Fortex/                       LE dépôt — Fortexworkshop/ia, branche dev
    ├── backend/                  API FastAPI : Service, Hub, store, messages, presence
    ├── sentinel/                 IA : anomaly.py, vision.py, sensors.py, alerts.py
    ├── presence/                 reconnaissance faciale et pointage par geste
    ├── firmware/sentinel-x/      ESP8266 (PlatformIO)
    ├── infra/                    Docker : Mosquitto, PostgreSQL, Prometheus, Grafana
    ├── dev/dashboard/            dashboard React (Vite)
    ├── scripts/                  lancement des briques, outillage, boîtier virtuel
    ├── tests/                    suite pytest
    ├── docs/
    │   ├── IA.md                 méthode et limites des deux briques d'IA
    │   ├── SECURITE.md           chiffrement, durée de vie, OWASP Top 10:2025
    │   ├── CHECKLIST.md          état d'avancement confronté au sujet
    │   ├── ORGANISATION.md       ce document
    │   ├── dossier/              chaîne de rendu : générateurs, assets, BENTO.md
    │   └── reference/            documents **tiers** (sujet, guide de méthodologie)
    ├── rendus/                   livrables (rendus/non/ : versions écartées, non versionnées)
    ├── README.md  CONTRIBUTING.md  DECISIONS.md
    └── .github/
```

---

## 3. Rôle des documents

| Document | Contenu | Pour qui |
|---|---|---|
| [`README.md`](../README.md) | le projet, l'architecture, comment le lancer | première lecture |
| [`CONTRIBUTING.md`](../CONTRIBUTING.md) | branches, commits, PR, secrets, chaîne de rendu | qui modifie le dépôt |
| [`DECISIONS.md`](../DECISIONS.md) | journal daté : quoi, pourquoi, options écartées | qui se demande « pourquoi ainsi ? » |
| [`docs/CHECKLIST.md`](CHECKLIST.md) | le sujet, point par point, et où l'on en est | préparation de la soutenance |
| [`docs/ORGANISATION.md`](ORGANISATION.md) | où vit quoi | ce document |
| [`docs/IA.md`](IA.md) | vision et maintenance prédictive : méthode, mesures, limites | jury technique |
| [`docs/SECURITE.md`](SECURITE.md) | matrice de chiffrement, durcissement, OWASP | jury technique |
| [`docs/dossier/BENTO.md`](dossier/BENTO.md) | authoring Bento (documentation de l'outil) | qui modifie le deck |
| [`dev/dashboard/CHARTE_GRAPHIQUE.md`](../dev/dashboard/CHARTE_GRAPHIQUE.md) | ISA-101, RGAA 4.1 AA, Core Web Vitals | qui touche l'IHM |
| [`presence/README.md`](../presence/README.md), [`infra/README.md`](../infra/README.md), [`firmware/README.md`](../firmware/README.md) | documentation de chaque module | qui touche au module |

`docs/reference/` ne contient que des **documents qui ne sont pas de nous** : le sujet du
workshop, le livret pédagogique et le support de cours IPSSI, et le guide de méthodologie. Ses
PDF sont sur le disque mais exclus du dépôt (§ 4).

---

## 4. Versionné ou pas

`rendus/` et `docs/dossier/` sont versionnés : ce sont la seule copie des livrables et de ce qui
les produit. Tout le reste des gros fichiers est ignoré.

| Chemin | Ignoré par | Pourquoi |
|---|---|---|
| `infra/.env` | `infra/.gitignore` | secrets générés par `configure.py` |
| `infra/certs/`, `infra/mosquitto/config/passwd`, `infra/mqtt-users.env` | `infra/.gitignore` | CA et comptes MQTT |
| `firmware/sentinel-x/include/sentinel_config.h` | `firmware/sentinel-x/.gitignore` | identifiants du boîtier |
| `data/` | `.gitignore` | empreintes faciales, journal de présence |
| `.env` | `.gitignore` | jeton d'API, code opérateur |
| `models/`, `.venv/`, `node_modules/`, `dist/` | `.gitignore` | poids, et reproductible |
| `docs/reference/*.pdf` | `.gitignore` | documents tiers dans un dépôt **public** |
| `rendus/non/` | `.gitignore` | versions écartées des livrables, gardées pour comparaison |
| `docs/dossier/*.html` | `.gitignore` | intermédiaires du rendu |

Règle générale : **ce qui se régénère ou se retélécharge n'est pas versionné** ; ce qui contient un
secret ou une donnée personnelle ne l'est jamais.

---

## 5. Les règles à ne pas enfreindre

1. **Ne jamais recréer de dépôt Git à la racine** de l'espace de travail (§ 1).
2. **`git add -A` uniquement depuis `Fortex/`** — depuis la racine, `Fortex/` deviendrait un
   sous-module bancal.
3. **Ne jamais committer** un PDF de `docs/reference/`, un fichier de `data/`, un `.env` ou un
   certificat : le dépôt est public.
4. **`git subtree push` seulement après avoir regardé l'écart** avec le dépôt d'origine.
   `--force` réécrit l'historique distant : c'est le seul geste irréversible de ce projet.
5. **Régénérer les rendus par les scripts**, jamais à la main : `docs/dossier/` est la source.

---

## 6. Dépôts distants et branches

| Dépôt | Branche par défaut | Rôle |
|---|---|---|
| `Fortexworkshop/ia` | `main` | le projet complet, `dev` et `infra` inclus par `git subtree` |
| `Fortexworkshop/dev` | `dev` | le dashboard React seul (sous-arbre) |
| `Fortexworkshop/infra` | `main` | l'infrastructure Docker seule (sous-arbre) |

**`dev` est la branche de travail ; `main` ne bouge que par PR.** Les trois dépôts sont publics.

```bash
# resynchroniser un sous-arbre depuis son dépôt d'origine
git subtree pull --prefix=dev   https://github.com/Fortexworkshop/dev.git   dev
git subtree pull --prefix=infra https://github.com/Fortexworkshop/infra.git main
```

Le flux de travail et les conventions de commit sont dans
[`CONTRIBUTING.md`](../CONTRIBUTING.md).
