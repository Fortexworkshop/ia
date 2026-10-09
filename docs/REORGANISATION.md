# Plan de réorganisation de l'espace de travail

Date : 2026-10-09 · Statut : **à valider** · Périmètre : l'espace de travail entier

Ce document décrit l'état constaté, la cible, et les étapes pour y arriver. Rien n'a été
exécuté : chaque phase est à valider avant d'être lancée.

---

## 1. Constat

### 1.1 Les trois problèmes

**1. La racine est un dépôt fantôme, et il est dangereux.**
`Workshop2026-M1/` est un dépôt Git dont le remote est `Fortexworkshop/dev`, mais qui ne suit
**aucun fichier**. Il a **2 commits d'avance** sur `origin/dev`, dont un commit qui **supprime
`dashboard/`**. Un `git push` depuis la racine **effacerait le dashboard du dépôt `dev`**.

| | Racine `Workshop2026-M1/` | `Fortex/` |
|---|---|---|
| Remote | `Fortexworkshop/dev` | `Fortexworkshop/ia` |
| Branche | `dev` | `dev` |
| Fichiers suivis | **0** | **142** |
| Écart avec le remote | **devant 2** | à jour |
| Modifications en attente | — | `M .gitignore`, `D CLAUDE.md` |

**2. Les trois dépôts GitHub sont publics, et `ia` publie une branche vide.**
`Fortexworkshop/ia` a **`main` par défaut** ; tout le travail est sur **`dev`**. Un visiteur voit
`main`, qui est en retard.

**3. Rien qui fasse le rendu n'est versionné.**
[`docs/dossier/`](dossier/) (les générateurs et leurs assets) est **hors suivi**. Le dossier, le
poster, le deck Bento et le `.pptx` ne sont donc **pas reproductibles depuis le dépôt**.

### 1.2 Ce qui va bien — à ne pas casser

- **Hygiène des secrets correcte** : aucun `.env`, certificat, mot de passe MQTT, donnée
  biométrique ni `sentinel_config.h` n'est suivi. Chaque exclusion est posée au bon niveau
  (`infra/.gitignore`, `firmware/sentinel-x/.gitignore`, `.gitignore`).

  | Chemin | Ignoré par |
  |---|---|
  | `infra/.env` | `infra/.gitignore:2` |
  | `infra/certs/` | `infra/.gitignore:36` |
  | `infra/mosquitto/config/passwd` | `infra/.gitignore:38` |
  | `infra/mqtt-users.env` | `infra/.gitignore:37` |
  | `data/` (empreintes, présences) | `.gitignore:3` |
  | `firmware/sentinel-x/include/sentinel_config.h` | `firmware/sentinel-x/.gitignore:2` |

- `node_modules`, `dist`, `models/`, `.venv/` sont couverts.
- `Fortex/dev` et `Fortex/infra` sont bien des `git subtree` (l'historique est présent).

### 1.3 L'état du disque

| Élément | Taille | Suivi ? | Remarque |
|---|---|---|---|
| `Bento/` (vieux deck, `SKILL.md`, compte-rendu) | 756 K | non | hors projet |
| `reference/` (sujet EPSI, livret + support IPSSI, GUIDE, CHECKLIST) | 2,1 M | non | **3 PDF tiers** |
| `rendus/` (ancien jeu de l'équipe + `neuf/`) | 6,0 M | non | ancien et nouveau mélangés |
| `CLAUDE.md`, `.github/`, `.vscode/` | 21 K | non | consignes en dehors du projet |
| `docs/dossier/slides.py`, `svg2png.js` | 23 K | non | **code mort** |
| `docs/dossier/dossier.html`, `poster.html` | 295 K | ignorés | intermédiaires, normal |
| `data/` (`faces.npz`, `people.db`, `presence_log.db`) | 68 K | ignorés | données biométriques |
| `.venv/`, `dev/dashboard/`, `models/` | 716 M | ignorés | normal |

---

## 2. Cible

```
Workshop2026-M1/                  ← espace de travail, PLUS AUCUN dépôt ici
└── Fortex/                       ← LE dépôt : Fortexworkshop/ia, branche dev
    ├── backend/ dev/ firmware/ infra/ presence/ scripts/ sentinel/ tests/
    ├── docs/
    │   ├── IA.md  SECURITE.md
    │   ├── REORGANISATION.md     ← ce document
    │   ├── dossier/              ← chaîne de rendu versionnée + assets/
    │   ├── bento/                ← SKILL.md, et l'ancien deck en archive/
    │   └── reference/            ← GUIDE, CHECKLIST  (les PDF tiers restent sur le disque,
    │                                exclus du dépôt)
    ├── rendus/                   ← livrables finaux
    │   └── archive-2026-10-08/   ← ancien jeu de l'équipe
    ├── .github/copilot-instructions.md
    ├── .vscode/mcp.json
    └── README.md
```

**Principe** : un seul dépôt, `Fortex`, et rien qui vive à côté. C'est déjà la règle du projet
(« aucun fichier hors de `Fortex` ne doit être suivi ») — il reste à la rendre vraie sur le disque.

---

## 3. Plan

### Phase 0 — Sauvegarder *(obligatoire, la phase 1 est irréversible)*

```bash
tar czf ~/sauvegarde-workshop-$(date +%F).tar.gz \
  -C ~/Code Workshop2026-M1 --exclude=.venv --exclude=node_modules --exclude=models
```

Les livrables ne sont versionnés nulle part : c'est leur seule copie.

### Phase 1 — Neutraliser le dépôt racine

```bash
cd ~/Code/Workshop2026-M1
git status -sb        # attendu : « devant 2 », aucun fichier suivi
rm -rf .git           # le piège disparaît ; dashboard/ reste intact sur GitHub
```

**Ne jamais pousser ce dépôt.** `rm -rf .git` est la seule façon sûre de le retirer.

### Phase 2 — Regrouper dans `Fortex/`

| Depuis | Vers | Remarque |
|---|---|---|
| `Bento/SKILL.md` | `Fortex/docs/bento/SKILL.md` | outil, à garder |
| `Bento/*.bento.html`, `Bento/COMPTE_RENDU.md` | `Fortex/docs/bento/archive/` | historique du 7 octobre |
| `reference/GUIDE_Methodologie_Rigoureuse.md` | `Fortex/docs/reference/` | à versionner |
| `reference/CHECKLIST.md` | `Fortex/docs/reference/` | à versionner |
| `reference/*.pdf` | `Fortex/docs/reference/` | **exclus du dépôt** (droits + dépôt public) |
| `rendus/neuf/*` | `Fortex/rendus/` | livrables finaux |
| `rendus/Workshop2026-M1-G20-*` + `*Pres.pptx` | `Fortex/rendus/archive-2026-10-08/` | ancien jeu |
| `CLAUDE.md` (racine) | `Fortex/CLAUDE.md` **ou** supprimé | doublon de `copilot-instructions.md` |
| `.github/copilot-instructions.md` | `Fortex/.github/` | le projet vit là |
| `.vscode/mcp.json` | `Fortex/.vscode/` | idem |
| `.gitignore` (racine) | supprimé | `dev/dashboard/.gitignore` couvre déjà `node_modules` et `dist` |

### Phase 3 — Nettoyer le dépôt `ia`

```bash
cd Fortex
rm docs/dossier/slides.py docs/dossier/svg2png.js    # code mort (voie PDF/PPTX abandonnée)
rm -rf .pytest_cache
```

Puis :

- [ ] **Ajouter au suivi** `docs/dossier/` : les 5 scripts (`build.py`, `bento.py`,
      `bento2pptx.py`, `bento_check.js`, `render.js`) et `assets/` (4 fichiers, 222 K).
- [ ] **Ajouter** à `.gitignore` : `docs/reference/*.pdf`.
- [ ] **Trancher** les deux modifications en attente : `M .gitignore` (à committer) et
      `D CLAUDE.md` (décider où va ce contenu).
- [ ] **Décider** du sort de `data/` (biométrie) : purger, ou déplacer hors de l'arbre de travail.
- [ ] **Passe sur le `README.md`** : il mélange le projet avec un module de pointage de présence
      (`presence/`, ex-directive) ; à réduire au périmètre du sujet.

### Phase 4 — Figer les livrables

Dans `Fortex/rendus/`, noms définitifs (≈ 1,7 Mo au total) :

| Fichier | Format |
|---|---|
| `Workshop2026-M1-G20-Dossier.pdf` | 17 p. A4 |
| `Workshop2026-M1-G20-Poster.pdf` | 1 p. A3 portrait |
| `SENTINEL-X-G20.bento.html` (+ `.json`) | deck de soutenance |
| `Workshop2026-M1-G20-Pres.pptx` | export PowerPoint éditable |

- [ ] Décider : versionner les binaires, ou ne versionner que les **sources** et régénérer.

### Phase 5 — Réaligner les trois dépôts

```bash
cd Fortex
git fetch origin
git log --oneline origin/dev -3          # vérifier l'écart AVANT de pousser
git subtree push --prefix=dev   https://github.com/Fortexworkshop/dev.git   dev
git subtree push --prefix=infra https://github.com/Fortexworkshop/infra.git main
git push origin dev
# puis fusionner dev -> main sur ia, pour que la branche par défaut montre le travail
```

> **Risque.** `Fortexworkshop/dev` a reçu `dashboard/` par un push direct antérieur. Si les
> histoires ont divergé, `git subtree push` refuse en fast-forward et exige `--force`, qui
> réécrit l'historique du remote. À contrôler **avant**, jamais à l'aveugle.

### Phase 6 — Vérifier

```bash
git -C Fortex status --short
git -C Fortex ls-files | grep -Ei "\.env$|certs/|passwd|faces|people\.db"   # attendu : vide
.venv/bin/python -m pytest -q                                             # attendu : 114 passés
python docs/dossier/build.py --group 20 --out rendus
python docs/dossier/bento.py --group 20 --out rendus
python docs/dossier/bento2pptx.py --group 20
```

---

## 4. Les pièges à ne pas déclencher

1. **Pousser la racine** → `dashboard/` disparaît de `Fortexworkshop/dev`.
2. **`git add -A` depuis la racine** une fois `Fortex/` en place → `Fortex` deviendrait un
   sous-module bancal.
3. **Commiter `reference/*.pdf`** → le sujet EPSI et les supports de formation IPSSI sont des
   documents tiers, dans un dépôt **public**.
4. **Commiter `data/`** → empreintes faciales et journal de présence.
5. **`git subtree push --force`** sans avoir regardé l'écart avec le remote.

---

## 5. Ordre et découpage

`0 → 1 → 2 → 3 → 4 → 5 → 6`

Committer `ia` **à la fin de chaque phase** plutôt qu'en un seul bloc, pour que chaque étape
reste annulable.

- Phases 0 à 1 : 10 min, sans risque si la sauvegarde est faite.
- Phases 2 à 4 : 30 min, purement local.
- Phase 5 : la seule qui touche des dépôts distants — à faire à froid.
